# Plugging in the band's mailbox

Roadie sends and receives through one shared mailbox, set up as a Frappe **Email Account**. Every email written in Roadie leaves from that address, every reply lands in Roadie's Inbox, and replies to an email sent from a gig thread back onto that gig.

This guide uses an OVH mailbox (the one that comes with an OVH domain). Any provider with IMAP and SMTP works the same way; only the server names change.

## Before you start

- The mailbox address and its password, e.g. `booking@your-band.com`. Check them once in the provider's webmail.
- The server settings. For OVH:

  | | Server | Port | Security |
  |---|---|---|---|
  | Incoming (IMAP) | `ssl0.ovh.net` | 993 | SSL |
  | Outgoing (SMTP) | `ssl0.ovh.net` | 465 | SSL |

  The login is the full email address.
- A Roadie site of its own (see the README): Band Members see every email on the site.
- The site's scheduler running. Frappe fetches new mail and sends queued mail from scheduled jobs, so without it nothing comes in and nothing goes out:

  ```bash
  bench --site <your-site> enable-scheduler
  ```

## Create the Email Account

Log in as Administrator, open `/app/email-account/new`, and fill in:

**Account**
- Email Address: `booking@your-band.com`
- Email Account Name: the band's name, e.g. `Acme Band`. Recipients see it as the sender name.
- Email Service: leave empty (OVH is not in the list).
- Method: Basic. Password: the mailbox password.

**Incoming**
- Enable Incoming: ticked
- Use IMAP: ticked. Incoming Server: `ssl0.ovh.net`, Port `993`, Use SSL: ticked
- IMAP Folder: `INBOX`
- Default Incoming: ticked
- Append To: **leave empty**. Roadie links mail to gigs by thread and to directory entries by contact; Append To would instead turn every new email into a document of that type.
- Email Sync Option: `UNSEEN`. Initial Sync Count: `100` (how many existing emails the first sync imports; raise it to bring in more history).

**Outgoing**
- Enable Outgoing: ticked
- Outgoing Server: `ssl0.ovh.net`, Port `465`, Use SSL for Outgoing: ticked (and Use TLS unticked)
- Default Outgoing: ticked
- **Always use this email address as sender address: ticked.** Without it, email goes out from the member's own address and replies never reach the shared Inbox.
- Always use this name as sender name: ticked, so emails read "Acme Band" rather than the bandmate's name.
- Append Emails to Sent Folder: ticked, with Sent Folder Name `Sent`. Emails sent from Roadie then also show in OVH webmail's Sent folder.

Save. Frappe logs into both servers when saving, so a wrong password or server fails right there with the server's error message.

## Check it works

1. In Roadie, open a gig and send an email to an address you can read (your personal mailbox).
2. The Outbox shows it as queued, then sent within a few minutes. If it stays queued, the scheduler is not running.
3. Reply to it from your personal mailbox.
4. Within a few minutes the reply shows unread in the Inbox and in the gig's thread. To fetch at once instead of waiting:

   ```bash
   bench --site <your-site> execute frappe.email.doctype.email_account.email_account.pull
   ```

## When it goes wrong

- **Save fails with an authentication error:** the password, or the login is not the full address. Log into OVH webmail with the same pair to rule out the mailbox itself.
- **Outbox stuck on queued:** the scheduler is off (`bench --site <your-site> doctor` shows it), or the workers are down.
- **Outbox shows error:** open the Email Queue entry from the Desk (`/app/email-queue`); it holds the SMTP server's refusal.
- **Replies never arrive:** check Enable Incoming and the IMAP folder, then look at `/app/error-log` for pull errors. A reply only threads onto its gig if the recipient replied to the email (not wrote a new one); a new email still lands in the Inbox and on the directory entry of the contact who sent it.
- **Recipients see a bandmate's address:** "Always use this email address as sender address" is unticked.
