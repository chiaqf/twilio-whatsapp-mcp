#!/usr/bin/env python3
"""MCP Server for Twilio WhatsApp messaging via Content Templates."""

import json
import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("twilio_whatsapp_mcp")

# Configuration from environment
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM", "")

MESSAGES_URL = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages.json"
CONTENT_URL = "https://content.twilio.com/v1/Content"


async def _twilio_request(
    method: str, url: str, data: dict | None = None, params: dict | None = None
) -> dict:
    """Make an authenticated request to the Twilio API."""
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method,
            url,
            auth=(ACCOUNT_SID, AUTH_TOKEN),
            data=data,
            params=params,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


def _handle_error(e: Exception) -> str:
    """Format API errors into actionable messages."""
    if isinstance(e, httpx.HTTPStatusError):
        status = e.response.status_code
        try:
            body = e.response.json()
            msg = body.get("message", e.response.text)
        except Exception:
            msg = e.response.text
        if status == 401:
            return f"Error: Authentication failed. Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN. ({msg})"
        if status == 404:
            return f"Error: Resource not found. Verify the SID is correct. ({msg})"
        if status == 429:
            return "Error: Rate limit exceeded. Wait before retrying."
        return f"Error: Twilio API returned {status}. {msg}"
    if isinstance(e, httpx.TimeoutException):
        return "Error: Request timed out. Try again."
    return f"Error: {type(e).__name__}: {e}"


@mcp.tool(
    name="send_whatsapp",
    annotations={
        "title": "Send WhatsApp Message",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def send_whatsapp(
    to: str, content_sid: str, content_variables: dict | str | None = None
) -> str:
    """Send a WhatsApp message using a Content Template.

    Args:
        to: Recipient phone number in E.164 format (e.g. +60126021369).
        content_sid: Content Template SID starting with HX.
        content_variables: Optional JSON object or string mapping template variable
            positions to values (e.g. {"1": "John", "2": "Order ready"}).

    Returns:
        JSON with the message SID and status on success, or an error string.
    """
    try:
        if content_variables and isinstance(content_variables, dict):
            content_variables = json.dumps(content_variables)
        payload = {
            "To": f"whatsapp:{to}",
            "From": f"whatsapp:{WHATSAPP_FROM}",
            "ContentSid": content_sid,
        }
        if content_variables:
            payload["ContentVariables"] = content_variables

        result = await _twilio_request("POST", MESSAGES_URL, data=payload)
        return json.dumps(
            {
                "message_sid": result["sid"],
                "status": result["status"],
                "to": result["to"],
                "date_created": result["date_created"],
            },
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="send_bulk_messages",
    annotations={
        "title": "Send Bulk WhatsApp Messages",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def send_bulk_messages(
    recipients: list[str], content_sid: str, content_variables: dict | str | None = None
) -> str:
    """Send the same Content Template to multiple WhatsApp recipients.

    Args:
        recipients: List of phone numbers in E.164 format.
        content_sid: Content Template SID starting with HX.
        content_variables: Optional JSON variables applied to all messages.

    Returns:
        JSON with results for each recipient (message SID or error).
    """
    if content_variables and isinstance(content_variables, dict):
        content_variables = json.dumps(content_variables)
    results = []
    for number in recipients:
        try:
            payload = {
                "To": f"whatsapp:{number}",
                "From": f"whatsapp:{WHATSAPP_FROM}",
                "ContentSid": content_sid,
            }
            if content_variables:
                payload["ContentVariables"] = content_variables

            result = await _twilio_request("POST", MESSAGES_URL, data=payload)
            results.append(
                {"to": number, "message_sid": result["sid"], "status": result["status"]}
            )
        except Exception as e:
            results.append({"to": number, "error": _handle_error(e)})

    return json.dumps(results, indent=2)


@mcp.tool(
    name="check_message_status",
    annotations={
        "title": "Check Message Delivery Status",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def check_message_status(message_sid: str) -> str:
    """Check the delivery status of a sent WhatsApp message.

    Args:
        message_sid: The message SID starting with SM, returned after sending.

    Returns:
        JSON with the message status, timestamps, and error info if any.
    """
    try:
        url = f"https://api.twilio.com/2010-04-01/Accounts/{ACCOUNT_SID}/Messages/{message_sid}.json"
        result = await _twilio_request("GET", url)
        return json.dumps(
            {
                "sid": result["sid"],
                "status": result["status"],
                "to": result["to"],
                "from": result["from"],
                "date_sent": result.get("date_sent"),
                "date_updated": result.get("date_updated"),
                "error_code": result.get("error_code"),
                "error_message": result.get("error_message"),
            },
            indent=2,
        )
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="list_messages",
    annotations={
        "title": "List WhatsApp Messages",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def list_messages(
    to: str | None = None,
    from_number: str | None = None,
    date_sent: str | None = None,
    limit: int = 20,
) -> str:
    """List recent WhatsApp messages with optional filters.

    Args:
        to: Filter by recipient phone number (E.164 format).
        from_number: Filter by sender phone number (E.164 format).
        date_sent: Filter by date sent (YYYY-MM-DD).
        limit: Maximum number of results to return (default 20).

    Returns:
        JSON array of messages with SID, status, to, from, date, and body.
    """
    try:
        params: dict = {"PageSize": min(limit, 100)}
        if to:
            params["To"] = f"whatsapp:{to}"
        if from_number:
            params["From"] = f"whatsapp:{from_number}"
        if date_sent:
            params["DateSent"] = date_sent

        result = await _twilio_request("GET", MESSAGES_URL, params=params)
        messages = [
            {
                "sid": m["sid"],
                "status": m["status"],
                "to": m["to"],
                "from": m["from"],
                "date_sent": m.get("date_sent"),
                "body": m.get("body"),
            }
            for m in result.get("messages", [])
        ]
        return json.dumps(messages, indent=2)
    except Exception as e:
        return _handle_error(e)


@mcp.tool(
    name="list_templates",
    annotations={
        "title": "List Content Templates",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def list_templates() -> str:
    """List all Content Templates in the Twilio account.

    Returns:
        JSON array of templates with SID, friendly name, variables, and types.
    """
    try:
        result = await _twilio_request("GET", CONTENT_URL)
        templates = []
        for t in result.get("contents", []):
            templates.append(
                {
                    "sid": t["sid"],
                    "friendly_name": t.get("friendly_name"),
                    "variables": t.get("variables"),
                    "types": list(t.get("types", {}).keys()),
                    "date_created": t.get("date_created"),
                }
            )
        return json.dumps(templates, indent=2)
    except Exception as e:
        return _handle_error(e)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
