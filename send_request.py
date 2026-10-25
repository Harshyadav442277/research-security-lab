"""Send a signed demo request to the lab's loopback server."""
import argparse
import http.client
import json
import sys
import time
import uuid

from policy import KEYS, encode, sign


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--key", choices=KEYS, default="alice")
    parser.add_argument("--request-id", default=None, help="Reuse an ID to try a duplicate delivery")
    parser.add_argument("--resource", default="device-a")
    parser.add_argument("--url", default="https://telemetry.example.test/ingest")
    parser.add_argument("--value", default="temperature=21")
    parser.add_argument("--timestamp", type=int, default=None, help="Unix seconds; defaults to now")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")

    request_id = args.request_id if args.request_id is not None else uuid.uuid4().hex
    timestamp = args.timestamp if args.timestamp is not None else int(time.time())
    body = encode(dict(request_id=request_id, timestamp=timestamp, tool="emit",
                       resource=args.resource, url=args.url, value=args.value))
    # The destination is always local. --url is a field for the policy to check,
    # not a network destination for this client or the recording sink.
    connection = http.client.HTTPConnection("127.0.0.1", args.port, timeout=5)
    try:
        connection.request("POST", "/execute", body=body,
                           headers={"Content-Type": "application/json", "X-Key-Id": args.key,
                                    "X-Signature": sign(body, args.key)})
        response = connection.getresponse()
        result = json.loads(response.read())
    except (OSError, http.client.HTTPException, ValueError) as error:
        print(f"Could not read the local server's response: {error}", file=sys.stderr)
        return 2
    finally:
        connection.close()
    print(f"{response.status} {result['reason']} (request_id={request_id})")
    return 0 if response.status == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())
