import { useState } from 'react'
import { ScrollArea } from '../ui/scroll-area'
import TaskCard from '../tasks/TaskCard'
import type { Task } from '../../types/recording'
import { createTask } from '../../services/api'

interface Props {
  tasks: Task[]
  meetingId?: string
}

export default function TasksTab({ tasks, meetingId }: Props) {
  const [localTasks, setLocalTasks] = useState<Task[]>(tasks)

  const handleCreate = async (taskId: string) => {
    if (meetingId) {
      await createTask(meetingId, taskId).catch(() => {})
    }
    setLocalTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: 'created' as const } : t))
    )
  }

  const handleReject = (taskId: string) => {
    setLocalTasks((prev) =>
      prev.map((t) => (t.id === taskId ? { ...t, status: 'rejected' as const } : t))
    )
  }

  if (tasks.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
        Задачи появятся после обработки встречи
      </div>
    )
  }

  const displayTasks = localTasks.length > 0 ? localTasks : tasks

  return (
    <ScrollArea className="h-full px-3 py-2">
      {displayTasks.map((task) => (
        <TaskCard
          key={task.id}
          task={task}
          onCreateTask={handleCreate}
          onRejectTask={handleReject}
        />
      ))}
    </ScrollArea>
  )
}
