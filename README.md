# Chess Agent A2A

This is a sample A2A agent that plays Chess! Given a chess move (in chess notation like e4) in A2A format. Watch a demo here.

[![CHESS A2A DEMO](https://img.youtube.com/vi/Y-8_7jBtt_4/0.jpg)](https://www.youtube.com/watch?v=Y-8_7jBtt_4)

## Example

This section shows example requests and responses that the agent supports.

### Example request with immediate response:

```
{
  "jsonrpc": "2.0",
  "id": "2fb94e55d13846e0bd01e49015774402",
  "method": "message/send",
  "params": {
    "message": {
      "kind": "message",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "e4",
          "metadata": null
        }
      ],
      "metadata": {
        "telex_user_id": "0192142c-02cc-7a41-b8bf-d0b7dc73d91b",
        "telex_channel_id": "019774df-2424-7fee-9dae-0e78860fed1e"
      },
      "messageId": "aec326cb185a4f28a2febfc2f2c914e8",
      "contextId": "019774df-2424-7fee-9dae-0e78860fed1e",
      "taskId": null
    },
    "configuration": null,
    "metadata": null
  }
}
```

#### Response

```
{
  "jsonrpc": "2.0",
  "id": "cbd99b993a8a492caf1f2b15202112b1",
  "result": {
    "id": "c4ca5c147a1c4f3caf1c751009aab1a8",
    "kind": "task",
    "contextId": null,
    "status": {
      "state": "input-required",
      "message": {
        "kind": "message",
        "role": "agent",
        "parts": [
          {
            "kind": "text",
            "text": "AI moved e7e5",
            "metadata": null
          },
          {
            "kind": "file",
            "file": {
              "name": "river_sky_stone.svg",
              "mimeType": "image/svg+xml",
              "bytes": null,
              "uri": "https://media.tifi.tv/telexbucket/public/chessagent/river_sky_stone.png"
            },
            "metadata": null
          }
        ],
        "metadata": null,
        "messageId": "e276ed16920e42009d61171810650280",
        "contextId": null,
        "taskId": null
      },
      "timestamp": "2025-06-26T12:34:35.889376"
    },
    "artifacts": null,
    "history": null,
    "metadata": null
  },
  "error": null
}
```


### Example webhook request

```
{
  "jsonrpc": "2.0",
  "id": "ff483cd0c8b244299526d49853586fb9",
  "method": "message/send",
  "params": {
    "message": {
      "kind": "message",
      "role": "user",
      "parts": [
        {
          "kind": "text",
          "text": "d4",
          "metadata": null
        }
      ],
      "metadata": {
        "telex_user_id": "0192142c-02cc-7a41-b8bf-d0b7dc73d91b",
        "telex_channel_id": "019778c7-2eed-7546-8a03-a56f7faa8992"
      },
      "messageId": "2508c40bf5b54da594ab13b545c299cb",
      "contextId": null,
      "taskId": null
    },
    "configuration": {
      "acceptedOutputModes": [
        "text/plain",
        "image/png",
        "image/jpg"
      ],
      "historyLength": 1,
      "pushNotificationConfig": {
        "url": "https://platformwebhookurl",
        "token": null,
        "authentication": {
          "schemes": [
            "platformapikey"
          ],
          "credentials": "platformcredentials"
        }
      },
      "blocking": false
    },
    "metadata": null
  }
}
```

#### Immediate Response

```
{
  "jsonrpc": "2.0",
  "id": "c1205500af0342fa9452a575346b0973",
  "result": {
    "id": "fe3e3a2a15f64e609f1eb8e136a2c30b",
    "contextId": null,
    "status": {
      "state": "working",
      "message": null,
      "timestamp": "2025-06-24T21:13:34.072364"
    },
    "artifacts": null,
    "history": null,
    "metadata": null
  },
  "error": null
}
```

#### Subsequent Webhook Response

```
{
  "jsonrpc": "2.0",
  "id": "cfe8025385ba4712ba96ee3da292b5e8",
  "result": {
    "id": "fe3e3a2a15f64e609f1eb8e136a2c30b",
    "contextId": null,
    "status": {
      "state": "input-required",
      "message": {
        "kind": "message",
        "role": "agent",
        "parts": [
          {
            "kind": "text",
            "text": "AI moved g8f6",
            "metadata": null
          },
          {
            "kind": "file",
            "file": {
              "name": "mountain_tree_light.svg",
              "mimeType": "image/svg+xml",
              "bytes": null,
              "uri": "https://media.tifi.tv/telexbucket/public/chessagent/mountain_tree_light.png"
            },
            "metadata": null
          }
        ],
        "metadata": null,
        "messageId": "f8894e7ac28548359f056507b38e6ed3",
        "contextId": null,
        "taskId": null
      },
      "timestamp": "2025-06-24T21:13:35.097126"
    },
    "artifacts": null,
    "history": null,
    "metadata": null
  },
  "error": null
}

```

## Deploying

You can deploy this agent as a Python application with the following ENV creds

```
PORT=5001
CHESS_ENGINE_PATH=/usr/local/bin/stockfish
MINIO_ENDPOINT=media.tifi.tv
MINIO_BUCKET_NAME=mybucket
MINIO_BUCKET_ACCESS_KEY=mybucketaccesskey
MINIO_BUKCET_SECRET_KEY=mybucketsecretkey

DEPLOYMENT_TYPE=webhook
```

You generally need a Chess engine like [Stockfish](https://stockfishchess.org/) for the in-game AI to function. You should also supply Minio (or S3) details for the agent to save moves and send it to the A2A client. You could optionally include a `DEPLOYMENT_TYPE` env var to specify if the agent should support push notification responses. The default for this webhook mode is false. If activated, the agent will respond via the provided webhook url.
