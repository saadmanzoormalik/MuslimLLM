# Guest Account Conversion

Email or social authentication while a guest is active converts the workspace inside one PostgreSQL transaction:

```text
verify permanent identity -> lock guest -> move projects -> move chats
-> merge settings -> move onboarding profile -> revoke guest sessions
-> mark guest converted -> create user session
```

IDs and timestamps stay unchanged. A converted guest cannot be converted again to another user. Any failure rolls back the transfer.
