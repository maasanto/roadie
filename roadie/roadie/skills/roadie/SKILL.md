---
name: roadie
domain: GENERAL
model: fast
description: >
  Works the band's bookings in Roadie: the gig pipeline, application deadlines, festivals,
  venues, promoters and bands, tasks, internal comments and emails linked to a gig. Use when
  someone asks about gigs, the pipeline, deadlines, the band's tasks or contacts, or wants to
  log, assign, comment on or email about a booking.
tools: [doc_list, doc_get, doc_create, doc_update, meta_get, method_call]
# Served to external agents via `dokos skill pull`: every tool it needs has a dokos-cli equivalent.
share: true
---

# Roadie

Roadie tracks the people, places and deadlines that get a band booked. Every member reads and
writes everything. The commands below use the `dokos` CLI; through MCP, `get-list` is
`doc_list`, `insert` is `doc_create`, `set-value` is `doc_update` and `call` is `method_call`.

## Domain model

Records are named by a random hash, so always look a record up by `title` first and use its `name`.

- **Gig** — a booking being chased: `title`, `status`, `gig_owner` (User), `gig_date`, `festival`, `festival_edition`, `venue`, `promoter`, `application_opens`, `application_closes`, `fee`, `notes`.
- **Festival** — `title`, `city`, `website`, `instagram`, `usual_month`, `notes`.
- **Festival Edition** — one year of a festival: `festival`, `year`, `start_date`, `end_date`, `website` (only when it differs from the festival's), `application_url`, `application_opens`, `application_closes`, `notes`.
- **Venue** — `title`, `city`, `website`, `instagram`, `capacity`, `address`, `notes`.
- **Promoter** — `title`, `city`, `website`, `instagram`, `notes`.
- **Band** — `title`, `city`, `website`, `instagram`, `genre` (a comma-separated list of genres), `notes`.
- **Band Task** — `title`, `assignee` (User), `gig`, `start_date`, `due_date`, `done`.
- **Roadie Settings** — one site-wide record; its `directory_columns` holds the columns each directory list and the gig list show, keyed by DocType.

Gig statuses, in pipeline order: `Idea`, `Contacted`, `Applied`, `Negotiating`, `Booked`, `Played`, `Declined`, `Dropped`.

The last two are dead ends, shown together in the pipeline's last column. A gig created with a `festival_edition`
and no window copies the edition's `application_opens` and `application_closes`, and its `festival` when that is
empty. The edition has to belong to the gig's festival.

People are standard Contacts, attached to a Festival, Venue, Promoter or Band through a Dynamic
Link. Internal discussion is a Comment, never emailed. Email is a Communication linked to its
Gig, and Frappe also links it to the directory record of every contact it was sent to.

## Recipes

Pipeline, grouped by status in the order above:

```bash
dokos get-list Gig --fields '["name","title","status","gig_date","application_closes","gig_owner","festival","venue","promoter"]' --filters '[["status","not in",["Declined","Dropped"]]]' --order-by "gig_date asc" --limit 500 --quiet
```

Applications closing in the next N days, for gigs not applied to yet (the dates are today and today + N):

```bash
dokos get-list Gig --fields '["name","title","status","application_closes","gig_owner"]' --filters '[["status","in",["Idea","Contacted"]],["application_closes","between",["2026-10-10","2026-10-24"]]]' --order-by "application_closes asc" --quiet
```

Create a gig from a festival edition. Find the festival and its edition for the year, then insert the gig with the
edition's `name`:

```bash
dokos get-list Festival --fields '["name","title","city"]' --filters '[["title","like","%Acme%"]]' --quiet
dokos get-list "Festival Edition" --fields '["name","year","application_url","application_closes"]' --filters '[["festival","=","<festival name>"],["year","=",2027]]' --quiet
dokos insert '{"doctype":"Gig","title":"Acme Festival 2027","festival_edition":"<edition name>","status":"Idea","gig_owner":"john@example.com"}' --quiet
```

Add a task and assign it to a member. List the members first; only they can be assigned:

```bash
dokos call roadie.api.get_members --get --quiet
dokos insert '{"doctype":"Band Task","title":"Send the rider","gig":"<gig name>","assignee":"jane@example.com","due_date":"2026-10-20"}' --quiet
```

Someone's open tasks, and ticking one done:

```bash
dokos get-list "Band Task" --fields '["name","title","due_date","gig"]' --filters '[["assignee","=","jane@example.com"],["done","=",0]]' --order-by "due_date asc" --quiet
dokos set-value "Band Task" "<task name>" done 1 --quiet
```

Post a comment that mentions a member. The mention span notifies them; plain `@Jane` does not:

```bash
dokos call frappe.desk.form.utils.add_comment --args '{"reference_doctype":"Gig","reference_name":"<gig name>","comment_email":"john@example.com","comment_by":"John Doe","content":"<p><span class=\"mention\" data-type=\"mention\" data-id=\"jane@example.com\" data-label=\"Jane Doe\">@Jane Doe</span> can you call them?</p>"}' --quiet
dokos call roadie.api.get_comments --get --args '{"doctype":"Gig","name":"<gig name>"}' --quiet
```

Email about a gig. Take the address from the record's contacts, show the user the draft, and
send only once they approve it. The email joins the gig's thread:

```bash
dokos call roadie.api.get_contacts --get --args '{"doctype":"Festival","name":"<festival name>"}' --quiet
dokos call frappe.core.doctype.communication.email.make --args '{"doctype":"Gig","name":"<gig name>","recipients":["booking@example.com"],"subject":"Application for Acme Festival 2027","content":"<p>Hello,</p><p>…</p>","send_email":1}' --quiet
dokos call roadie.api.get_emails --get --args '{"doctype":"Gig","name":"<gig name>"}' --quiet
```

## Rules

- Confirm with the user before sending any email and before deleting anything. Show the exact recipients, subject and text.
- Never invent a contact, email address or member. If the record has no contact, say so and ask.
- Comments are internal to the band; never put a contact's address in one expecting it to be emailed.
- Leave `application_opens` and `application_closes` empty on a new festival gig so the edition's window is copied.
