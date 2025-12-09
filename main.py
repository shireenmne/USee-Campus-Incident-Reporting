import os
from datetime import datetime
from typing import Optional

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from models import Admin, Report, SQLModel
from passlib.context import CryptContext
from sqlmodel import Session, create_engine, desc, select
from starlette.middleware.sessions import SessionMiddleware

# Config
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.db")
SECRET_KEY = os.getenv("SECRET_KEY", "change_this_secret_for_prod")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", None)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Database Initialization
def init_db():
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        admin = db.exec(select(Admin)).first()
        if not admin:
            pw = (ADMIN_PASSWORD or "changeme")[:72]
            hashed = pwd_context.hash(pw)

            admin = Admin(username=ADMIN_USERNAME, password_hash=hashed)
            db.add(admin)
            db.commit()

            print(
                f"[init_db] Default admin created: username='{ADMIN_USERNAME}', password='{pw}'")


init_db()


# DB Dependency
def get_db():
    with Session(engine) as session:
        yield session


# Auth Helpers
def is_admin(request: Request):
    return bool(request.session.get("is_admin"))


def require_admin(request: Request):
    if not is_admin(request):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin login required."
        )


# Student Routes
@app.get("/", response_class=HTMLResponse)
def landing(request: Request):
    return templates.TemplateResponse("landing.html", {"request": request})


@app.get("/report", response_class=HTMLResponse)
def report_form(request: Request):
    return templates.TemplateResponse("report.html", {"request": request})


@app.post("/report")
def submit_report(request: Request,
                  token: Optional[str] = Form(""),  # Optional token
                  subject: str = Form(...),
                  description: str = Form(...),
                  db: Session = Depends(get_db)):

    token = token.strip() if token else None

    if not subject.strip() or not description.strip():
        return templates.TemplateResponse(
            "report.html",
            {"request": request, "error": "All fields are required."}
        )
    if token:
        existing = db.exec(select(Report).where(Report.token == token)).first()
        if existing:
            return templates.TemplateResponse(
                "report.html",
                {"request": request, "error": "Token collision: regenerate & try again."}
            )

    rpt = Report(
        token=token,
        subject=subject.strip(),
        description=description.strip(),
        submitted_at=datetime.utcnow(),
        status="Received",
    )
    db.add(rpt)
    db.commit()

    if token:
        return RedirectResponse(url=f"/report/success?token={token}",
                                status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse(url="/report/success", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/report/success", response_class=HTMLResponse)
def report_success(request: Request, token: Optional[str] = None):
    return templates.TemplateResponse("success.html", {"request": request, "token": token})


@app.get("/status", response_class=HTMLResponse)
def status_lookup(request: Request):
    return templates.TemplateResponse("status_lookup.html", {"request": request})


@app.post("/status")
def status_redirect(token: str = Form(...)):
    t = token.strip()
    return RedirectResponse(url=f"/status/{t}", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/status/{token}", response_class=HTMLResponse)
def status_view(request: Request, token: str, db: Session = Depends(get_db)):
    rpt = db.exec(select(Report).where(Report.token == token)).first()
    found = rpt is not None
    return templates.TemplateResponse(
        "status_view.html",
        {"request": request, "found": found, "report": rpt, "token": token}
    )


# Admin Routes
@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_get(request: Request):
    return templates.TemplateResponse("admin_login.html", {"request": request})


@app.post("/admin/login")
def admin_login_post(request: Request,
                     username: str = Form(...),
                     password: str = Form(...),
                     db: Session = Depends(get_db)):

    admin = db.exec(select(Admin).where(Admin.username == username)).first()
    if not admin or not pwd_context.verify(password, admin.password_hash):
        return templates.TemplateResponse(
            "admin_login.html",
            {"request": request, "error": "Invalid credentials."}
        )

    request.session["is_admin"] = True
    request.session["admin_username"] = admin.username
    return RedirectResponse("/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/admin/logout")
def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)


@app.get("/admin/dashboard", response_class=HTMLResponse)
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    require_admin(request)
    reports = db.exec(select(Report).order_by(
        desc(Report.submitted_at))).all()
    return templates.TemplateResponse("admin_dashboard.html",
                                      {"request": request, "reports": reports})


@app.get("/admin/report/{report_id}", response_class=HTMLResponse)
def admin_report_detail(request: Request,
                        report_id: int,
                        db: Session = Depends(get_db)):
    require_admin(request)
    rpt = db.get(Report, report_id)
    if not rpt:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse("admin_report.html",
                                      {"request": request, "report": rpt})


@app.post("/admin/report/{report_id}/status")
def admin_report_status(request: Request,
                        report_id: int,
                        new_status: str = Form(...),
                        db: Session = Depends(get_db)):
    require_admin(request)
    rpt = db.get(Report, report_id)
    if not rpt:
        raise HTTPException(status_code=404)

    rpt.status = new_status
    db.add(rpt)
    db.commit()

    return RedirectResponse(f"/admin/report/{report_id}",
                            status_code=status.HTTP_303_SEE_OTHER)


@app.post("/admin/report/{report_id}/delete")
def admin_report_delete(request: Request, report_id: int, db=Depends(get_db)):
    require_admin(request)
    rpt = db.query(Report).filter(Report.id == report_id).first()
    if not rpt:
        raise HTTPException(status_code=404)

    db.delete(rpt)
    db.commit()

    return RedirectResponse(url="/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)
