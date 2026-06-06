import { ScrollArea } from '../ui/scroll-area'
import TaskCard from '../tasks/TaskCard'
import type { Task } from '../../types/recording'

interface Props {
  tasks: Task[]
}

export default function TasksTab({ tasks }: Props) {
  if (tasks.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-muted-foreground">
        Задачи появятся после обработки встречи
      </div>
    )
  }

  return (
    <ScrollArea className="h-full px-3 py-2">
      {tasks.map((task) => (
        <TaskCard key={task.id} task={task} />
      ))}
    </ScrollArea>
  )
}
