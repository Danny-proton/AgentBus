# Command Logger Hook

Logs all command events for debugging, analytics, and system monitoring.

## What It Does

This hook captures and logs every command event:

1. **Command capture** - Records command name, arguments, and metadata
2. **Performance tracking** - Logs execution time and success/failure status
3. **User context** - Associates commands with user and session information
4. **Analytics data** - Provides data for command usage analysis
5. **Error tracking** - Special handling for failed commands

## Features

- **Universal logging** - Captures all command events automatically
- **Performance metrics** - Tracks execution time and success rates
- **Rich metadata** - Includes user, session, and context information
- **Configurable output** - Supports different logging formats and destinations
- **Rate limiting** - Prevents log spam from excessive commands
- **Privacy controls** - Option to exclude sensitive data

## Configuration

The hook supports optional configuration:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `enabled` | boolean | `true` | Enable/disable the hook |
| `priority` | integer | `-500` | Execution priority (low) |
| `timeout` | integer | `10` | Maximum execution time |
| `log_level` | string | `"INFO"` | Logging level |
| `include_args` | boolean | `true` | Include command arguments |
| `include_context` | boolean | `true` | Include context data |
| `sanitize_sensitive` | boolean | `true` | Remove sensitive data |

Example configuration:

```json
{
  "hooks": {
    "command-logger": {
      "enabled": true,
      "priority": -500,
      "timeout": 10,
      "log_level": "INFO",
      "include_args": true,
      "include_context": true,
      "sanitize_sensitive": true
    }
  }
}
```

## Log Format

Commands are logged in structured format:

```json
{
  "timestamp": "2024-12-01T14:30:22.123Z",
  "session_key": "session:123",
  "command": "analyze",
  "args": ["data.json"],
  "user_id": "user:456",
  "channel_id": "discord:789",
  "success": true,
  "duration_ms": 1250,
  "context": {
    "workspace_dir": "/workspace",
    "agent_id": "agent:main"
  }
}
```

## Use Cases

### Debugging
- Track which commands are being executed
- Identify slow or failing commands
- Monitor command usage patterns

### Analytics
- Command popularity metrics
- User engagement tracking
- Performance monitoring
- Usage pattern analysis

### Monitoring
- System health indicators
- Error rate tracking
- Capacity planning data
- Security monitoring

## Output Destinations

The hook can write to multiple destinations:

- **Console** - Direct console output
- **File** - Structured log files
- **Database** - Structured storage for queries
- **External services** - Integration with logging services

## Data Retention

Logged data can be retained based on:

- **Time-based** - Keep logs for specific duration
- **Size-based** - Limit total log file size
- **Count-based** - Maximum number of log entries
- **Priority-based** - Keep important logs longer

## Privacy and Security

The hook includes privacy controls:

- **Data sanitization** - Remove passwords, tokens, etc.
- **User anonymization** - Hash user IDs if needed
- **Sensitive field filtering** - Configurable field exclusions
- **GDPR compliance** - User data deletion capabilities

## Integration

This hook integrates with:

- **Analytics Dashboard** - Real-time command statistics
- **Performance Monitor** - Command execution metrics
- **Error Tracker** - Failed command analysis
- **User Activity Monitor** - User engagement tracking

## Performance Impact

The hook is designed to minimize performance impact:

- **Asynchronous logging** - Non-blocking operation
- **Buffer management** - Efficient batch processing
- **Configurable verbosity** - Control log detail level
- **Smart filtering** - Skip unnecessary data

## Troubleshooting

Common issues and solutions:

### High Log Volume
- Reduce log level
- Enable sampling
- Filter by command type

### Slow Performance
- Increase timeout
- Reduce context inclusion
- Use async logging

### Large Log Files
- Enable rotation
- Compress old logs
- Set retention policies