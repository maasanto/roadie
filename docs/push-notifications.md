# Turning on push notifications

With push on, every entry of Roadie's notification panel (assigned tasks, due-today and closing-soon reminders, mentions) also reaches each member's phone or computer as a system notification, even when Roadie is closed.

Roadie sends through Frappe's push relay, `frappe.push_notification`, under the project name `roadie`. The site never talks to Firebase itself: it hands each notification to a relay server, and the relay sends it through Firebase Cloud Messaging (FCM). Frappe's own relay is not open source, so this guide runs [metalmon/notification-relay](https://github.com/metalmon/notification-relay), a small Go server that speaks the same API.

## Before you start

- A Google account to own the Firebase project. Firebase's free plan covers push.
- A server for the relay, reachable over HTTPS from both the Roadie site and the members' browsers. It can be the server that runs Roadie, behind the same reverse proxy, on a subdomain such as `push.your-band.com`.
- Roadie served over HTTPS. Browsers only allow push on secure pages (`localhost` is the one exception, for testing).

## 1. Create the Firebase project

In the [Firebase console](https://console.firebase.google.com):

1. Create a project, e.g. `roadie-push`. Google Analytics is not needed. Creating it from the console also accepts the Firebase terms. `firebase projects:create` fails with a 403 on an account that has never accepted them.
2. Add a **Web app** (the `</>` icon on the project overview), named `Roadie`. Skip Hosting. Keep the `firebaseConfig` it shows: `apiKey`, `authDomain`, `projectId`, `storageBucket`, `messagingSenderId` and `appId`. It is public, the browser receives it anyway.
3. Project settings → **Cloud Messaging** → Web Push certificates → **Generate key pair**. Keep the public key (it starts with `B`). The relay does not need the private key.
4. Check that **Firebase Cloud Messaging API (V1)** shows as Enabled on the same tab. New projects have it on.
5. Project settings → **Service accounts** → **Generate new private key**. This downloads `service-account.json`. It is a secret: anyone holding it can send pushes as your project. Never commit it.

With the [Firebase CLI](https://firebase.google.com/docs/cli), steps 2 and the config can also be done from a terminal once the project exists:

```bash
firebase apps:create WEB Roadie --project roadie-push
firebase apps:sdkconfig WEB <app-id> --project roadie-push
```

## 2. Run the relay

Build it with Go 1.22 or later:

```bash
git clone https://github.com/metalmon/notification-relay
cd notification-relay
go build -o notification-relay .
```

**Patch it first.** Frappe's `FrappeClient.post_api` sends its parameters as a form body, and the relay only reads the URL query or a JSON body. Unpatched, the site's first registration fails with a 400 and Roadie's switch shows "the push relay refused this device (500)". Add this middleware in `main.go`, just before the "Normalize double slashes" one, then build:

```go
// Frappe's FrappeClient.post_api sends its parameters as a form body, while every handler reads c.Query.
router.Use(func(c *gin.Context) {
	if c.Request.Method == http.MethodPost && strings.HasPrefix(c.ContentType(), "application/x-www-form-urlencoded") {
		if err := c.Request.ParseForm(); err == nil {
			c.Request.URL.RawQuery = c.Request.Form.Encode()
		}
	}
	c.Next()
})
```

Put `service-account.json` next to a `config.json` like this one, filled with the values from step 1:

```json
{
    "projects": {
        "roadie": {
            "vapid_public_key": "B...",
            "firebase_config": {
                "apiKey": "AIza...",
                "authDomain": "roadie-push.firebaseapp.com",
                "projectId": "roadie-push",
                "storageBucket": "roadie-push.firebasestorage.app",
                "messagingSenderId": "1234567890",
                "appId": "1:1234567890:web:abc123"
            }
        }
    },
    "trusted_proxies": "127.0.0.1/32",
    "allowed_origins": ["https://roadie.your-band.com"]
}
```

- The project key must be `roadie`: that is the name Roadie asks the relay for.
- `allowed_origins` lists every address members open Roadie from, scheme and port included. The browser fetches the Firebase config from the relay directly, so any other origin gets a 403.

Start it:

```bash
LISTEN_PORT=5021 \
NOTIFICATION_RELAY_CONFIG=/etc/notification-relay/config.json \
GOOGLE_APPLICATION_CREDENTIALS=/etc/notification-relay/service-account.json \
GIN_MODE=release \
./notification-relay
```

`LISTEN_PORT` defaults to 5000, which macOS already uses for AirPlay. The relay writes `credentials.json` and `user-device-map.json` next to `config.json`, so that directory must be writable and backed up. Losing them means clearing the site's relay credentials (see below) and every device turning push on again.

In production, run it under systemd (or the repository's `docker-compose.yml`) and put it behind the HTTPS reverse proxy, e.g. nginx with `proxy_pass http://127.0.0.1:5021;` on `push.your-band.com`. Check it answers:

```bash
curl https://push.your-band.com/api/method/notification_relay.api.get_config?project_name=roadie
```

## 3. Point the site at the relay

```bash
bench --site <your-site> set-config push_relay_server_url https://push.your-band.com
bench --site <your-site> set-config host_name https://roadie.your-band.com
```

Then log into the Desk as Administrator, open `/app/push-notification-settings`, tick **Enable Push Notification Relay** and save.

`host_name` matters: on its first send, the site registers itself with the relay, and the relay checks the request by calling the site back at that address. It must be the site's public HTTPS address, reachable from the relay server. The site also needs its workers running, since pushes go out from a background job.

Roadie hides the push switch until both the relay URL and the setting are in place. A backup restored elsewhere keeps the setting but not the site config, so a copy of production never pushes to real members.

## 4. Each member turns it on

In Roadie, Settings → **Push notifications on this device**, then allow notifications when the browser asks. It is per device: a member with a laptop and a phone turns it on twice.

On an iPhone or iPad, open Roadie in Safari, Share → **Add to Home Screen**, and turn push on from the app on the Home Screen. Safari tabs cannot receive push, so the switch does not show there.

Logging out of Roadie turns push off on that device.

## Check it works

1. A member turns push on, then closes Roadie.
2. A bandmate assigns them a task.
3. The notification arrives within a few seconds. Clicking it opens Roadie on the task list.

## When it goes wrong

- **No push switch in Settings:** `push_relay_server_url` is missing or the setting is unticked, or the browser cannot do push (an iPhone tab before Add to Home Screen, a private window, plain HTTP).
- **"The push relay answered with an error (403)":** the address members use is missing from `allowed_origins`.
- **"The push relay refused this device (500)":** the site could not register with the relay. Look at the relay's log. A 400 on `get_credential` means the relay is unpatched. "Token verification failed" or a connection error means the relay cannot reach the site at `host_name`. A 401 means the relay lost its `credentials.json`: clear API Key and API Secret in Push Notification Settings so the site registers again.
- **The switch fails on Firebase:** "API key not valid" means `firebase_config` is wrong. "messaging/token-subscribe-failed" usually means the VAPID key belongs to another project.
- **The switch is on but nothing arrives:** look for `send_push` in the site's Error Log and for `sendNotificationToUser` in the relay's log. "not subscribed to push notifications" means the device token was dropped: turn push off and on again on that device. Check the operating system's notification settings for the browser too, since macOS and Windows can mute it.
