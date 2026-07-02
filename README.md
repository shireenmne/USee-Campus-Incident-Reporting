# USee — Anonymous Campus Incident Reporting

A web app that lets students report campus incidents anonymously — no account or login required. Reporters can optionally set a token to check on their report's status later, without ever having to identify themselves.

## Why I built this
I noticed a lot of students on my campus using an anonymous gossip app to talk about things that had happened to them — stuff that sounded like it should be reported, but wasn't, probably because people were scared to come forward. This was during a semester when I was deep in criminology coursework, and it got me thinking: if the fear of being identified is what's stopping people from speaking up, then removing that barrier could actually help. This was a class project I chose to build around that idea.

## How it works
- Students submit a report (subject + description) through a simple form
- They can optionally choose a token at submission — this is the only way to look up a report afterward, so there's no login, email, or identifying info tied to a report
- Admins log in separately (session-based auth, bcrypt-hashed passwords) to view incoming reports, update their status, and respond

## Tech stack
- **Backend:** FastAPI, SQLModel (SQLAlchemy)
- **Templating:** Jinja2
- **Auth:** Session-based (Starlette SessionMiddleware) for admins, bcrypt for password hashing
- **Database:** SQLite
- **Styling:** Custom CSS

## Status
Still actively working on this — cleaning up the codebase and adding features. Not production-ready yet (e.g. secrets/config need hardening before any real deployment).
