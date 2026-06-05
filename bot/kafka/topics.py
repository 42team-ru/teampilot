# Bot → Backend (producer)
FILES_UPLOADED      = "files.uploaded"
TOPIC_FILES_UPLOADED = FILES_UPLOADED
TOPIC_MESSAGES_RAW   = "messages.raw"
TOPIC_AUDIO_UPLOAD   = "audio.upload"
TOPIC_TASK_CONFIRMED = "tasks.confirmed"
TOPIC_TASK_REJECTED  = "tasks.rejected"
TOPIC_STATUS_CHANGED = "tasks.status"

# Backend → Bot (consumer)
TOPIC_TASK_PROPOSE  = "tasks.propose"
TOPIC_REMINDER_SEND = "reminders.send"
TOPIC_SUMMARY_SEND  = "summary.send"
TOPIC_BOTS_TASKS = "bots.tasks"
TOPIC_BOTS_NOTIFICATIONS = "bots.notifications"


class Topics:
    FILES_UPLOADED = FILES_UPLOADED
