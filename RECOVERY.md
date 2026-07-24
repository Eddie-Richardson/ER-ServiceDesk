# ER-ServiceDesk/RECOVERY.md

# Locked Out? Read This.

If you're locked out of your own admin account and there's nobody else
who can reset it for you, this gets you back in. You don't need to
know Docker for this -- just copy the command below exactly.

## Step 1 — Open PowerShell

Open PowerShell and make sure you're in your project folder:

```powershell
cd D:\Documents\Python Code\ER-ServiceDesk
```

## Step 2 — Run this exact command

```powershell
docker-compose exec -it api python -m app.db.reset_admin_password
```

The `-it` at the start matters -- without it, the next step won't work.

## Step 3 — Answer the prompts

It will ask you three things, one at a time:

1. **Email of the superuser account to reset** -- type your admin
   email (e.g. `admin@example.com`) and press Enter.
2. **New password** -- type a new password. It will NOT show on
   screen as you type -- that's normal, just type it and press Enter.
3. **Confirm new password** -- type the same password again.

If everything matches, it'll say:
```
Password reset successfully for <your email>.
```

You can now log into the app with that new password.

## If something goes wrong

- **"No account found with email..."** -- you typed the email wrong.
  Try again.
- **"...is not a superuser account"** -- this tool only resets admin
  accounts. If you're trying to reset a regular employee's password
  instead, log in as an admin and use the **Reset Password** button in
  the Users & Roles window instead.
- **"Passwords didn't match"** -- just run the command again and be
  careful typing the password the second time.

## Where to keep this file

Keep a copy of this file somewhere you can find it *without* being
logged into the app -- your desktop, a notes app, printed out, wherever
you'll actually remember to look during an actual lockout. A copy that
only exists inside the app is useless the one time you actually need
it.
