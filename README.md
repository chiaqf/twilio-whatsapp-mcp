# Twilio WhatsApp MCP Server

An MCP server that lets Claude send and manage WhatsApp messages via Twilio's REST API. All messages use pre-approved Content Templates.

## Setup

### 1. Add to Claude Desktop

Open your Claude Desktop config (`claude_desktop_config.json`) and add:

```json
{
  "mcpServers": {
    "twilio-whatsapp": {
      "command": "uvx",
      "args": ["--from", "git+https://github.com/chiaqf/twilio-whatsapp-mcp", "twilio-whatsapp-mcp"],
      "env": {
        "TWILIO_ACCOUNT_SID": "your-account-sid",
        "TWILIO_AUTH_TOKEN": "your-auth-token",
        "TWILIO_WHATSAPP_FROM": "+1234567890"
      }
    }
  }
}
```

Replace the `env` values with your Twilio credentials and WhatsApp-enabled phone number.

### 2. Get your Twilio credentials

- **Account SID** and **Auth Token**: Find these on your [Twilio Console dashboard](https://console.twilio.com/)
- **WhatsApp From number**: Your Twilio phone number enabled for WhatsApp (E.164 format, e.g. `+1234567890`)

### 3. Restart Claude Desktop

Restart Claude Desktop to pick up the new MCP server.

## Tools

| Tool | Description |
|------|-------------|
| `send_whatsapp` | Send a WhatsApp message using a Content Template |
| `send_bulk_messages` | Send a template to multiple recipients |
| `check_message_status` | Check delivery status of a sent message |
| `list_messages` | List recent messages with optional filters |
| `list_templates` | List all Content Templates in your account |

## Usage examples

**List your templates:**
> "List my WhatsApp templates"

**Send a message:**
> "Send a WhatsApp to +60126021369 using template HX5965f5747f9790e84f25aa69280da01c"

**Send with variables:**
> "Send a WhatsApp to +60126021369 using template HX... with variables name=John and status=Order ready"

**Check delivery:**
> "Check the status of message SM1234567890abcdef"

## Security

Your Twilio Auth Token is sensitive. Keep it in the Claude Desktop config (which is local to your machine) and do not commit it to version control. Rotate the token periodically via the [Twilio Console](https://console.twilio.com/).
