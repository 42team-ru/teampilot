import { useEffect, useState } from "react";
import type { CSSProperties } from "react";
import { useSearchParams } from "react-router-dom";
import { Plus, ChevronLeft, ChevronRight } from "lucide-react";
import {
  useTaskColumns,
  useTasksByColumn,
} from "@/hooks/useTasks";
import { useTeamMembers } from "@/hooks/useTeams";
import { useAppStore } from "@/stores/appStore";
import { TaskCard } from "@/components/common/TaskCard";
import { TaskDetailSheet } from "@/components/common/TaskDetailSheet";
import { CreateTaskSheet } from "@/components/common/CreateTaskSheet";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { TaskColumnResponse } from "@/api/types";

const columnScrollStyle: CSSProperties = {
  scrollbarWidth: "none",
  msOverflowStyle: "none",
};

function KanbanColumn({
  column,
  filterMemberId,
  onTaskClick,
}: {
  column: TaskColumnResponse;
  filterMemberId: string | null;
  onTaskClick: (id: string) => void;
}) {
  const { data } = useTasksByColumn(column.id);
  const tasks = (data?.content ?? []).filter(
    (t) => !filterMemberId || t.assignee?.teamUserId === filterMemberId,
  );

  return (
    <div className="w-full flex-1 flex flex-col min-h-0">
      <div className="rounded-xl border border-t-4 border-t-blue-400 bg-card flex flex-col flex-1 overflow-hidden">
        {/* Sticky column header */}
        <div className="px-3 py-2 flex items-center justify-between border-b flex-shrink-0">
          <span className="text-sm font-semibold">{column.title}</span>
          <span className="text-xs text-muted-foreground bg-muted rounded-full px-2 py-0.5">
            {tasks.length}
          </span>
        </div>
        {/* Scrollable task list with bottom fade */}
        <div className="relative flex-1 min-h-0">
          <div
            className="absolute inset-0 overflow-y-auto p-2 space-y-2"
            style={columnScrollStyle}
          >
            {tasks.map((task) => (
              <TaskCard
                key={task.id}
                task={task}
                onClick={() => onTaskClick(task.id)}
              />
            ))}
            {/* Bottom padding so last card isn't hidden under the fade */}
            <div className="h-6" />
          </div>
          {/* Bottom fade hint */}
          <div
            className="pointer-events-none absolute bottom-0 left-0 right-0 h-8"
            style={{
              background:
                "linear-gradient(to bottom, transparent, hsl(var(--card)))",
            }}
          />
        </div>
      </div>
    </div>
  );
}

export function BoardPage() {
  const activeTeam = useAppStore((s) => s.activeTeam);
  const [searchParams, setSearchParams] = useSearchParams();
  const { data: columns, isLoading } = useTaskColumns(
    activeTeam?.telegramChatId ?? undefined,
    activeTeam?.id,
  );
  const { data: members } = useTeamMembers(activeTeam?.id);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [filterMemberId, setFilterMemberId] = useState<string | null>(() =>
    searchParams.get("assignee"),
  );
  const [activeColIndex, setActiveColIndex] = useState(0);

  const activeCol = columns?.[activeColIndex] ?? columns?.[0];

  useEffect(() => {
    setFilterMemberId(searchParams.get("assignee"));
  }, [searchParams]);

  const updateAssigneeFilter = (memberId: string | null) => {
    setFilterMemberId(memberId);
    const nextParams = new URLSearchParams(searchParams);
    if (memberId) {
      nextParams.set("assignee", memberId);
    } else {
      nextParams.delete("assignee");
    }
    setSearchParams(nextParams, { replace: true });
  };

  const prev = () => setActiveColIndex((i) => Math.max(0, i - 1));
  const next = () =>
    setActiveColIndex((i) => Math.min((columns?.length ?? 1) - 1, i + 1));

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 pt-6 pb-3 flex items-center justify-between">
        <h1 className="text-xl font-bold">Доска</h1>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4 mr-1" />
          Задача
        </Button>
      </div>

      {members && members.length > 1 && (
        <div className="px-4 pb-3 flex items-center gap-2">
          <span className="flex-shrink-0 text-xs text-muted-foreground">
            Исполнитель
          </span>
          <div className="flex gap-2 overflow-x-auto scrollbar-none">
            <button
              onClick={() => updateAssigneeFilter(null)}
              className={cn(
                "flex-shrink-0 text-xs border rounded-full px-3 py-1.5 transition-colors",
                !filterMemberId
                  ? "bg-primary text-primary-foreground border-primary"
                  : "bg-background",
              )}
            >
              Все
            </button>
            {members.map((m) => (
              <button
                key={m.id}
                onClick={() =>
                  updateAssigneeFilter(m.id === filterMemberId ? null : m.id)
                }
                className={cn(
                  "flex-shrink-0 text-xs border rounded-full px-3 py-1.5 transition-colors",
                  m.id === filterMemberId
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-background",
                )}
              >
                {m.firstName ?? m.telegramLogin ?? m.telegramId}
              </button>
            ))}
          </div>
        </div>
      )}

      {isLoading && (
        <div className="flex gap-3 px-4">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="flex-shrink-0 w-20 h-8 rounded-full border animate-pulse bg-muted"
            />
          ))}
        </div>
      )}

      {!isLoading && (!columns || columns.length === 0) && (
        <div className="flex-1 flex items-center justify-center text-muted-foreground">
          <div className="text-center">
            <p className="text-4xl mb-3">📋</p>
            <p className="text-sm">
              Нет колонок. Настройте YouGile в профиле команды.
            </p>
          </div>
        </div>
      )}

      {columns && columns.length > 0 && (
        <>
          {/* Column pill tabs with prev/next arrows */}
          <div className="flex items-center gap-1 px-2 pb-3">
            <button
              onClick={prev}
              disabled={activeColIndex === 0}
              className={cn(
                "p-1 rounded-full",
                activeColIndex === 0 && "opacity-30",
              )}
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <div className="flex-1 flex gap-2 overflow-x-auto scrollbar-none justify-center">
              {columns.map((col, i) => (
                <button
                  key={col.id}
                  onClick={() => setActiveColIndex(i)}
                  className={cn(
                    "flex-shrink-0 text-xs rounded-full px-3 py-1.5 border transition-colors",
                    i === activeColIndex
                      ? "bg-primary text-primary-foreground border-primary"
                      : "border-border text-foreground",
                  )}
                >
                  {col.title}
                </button>
              ))}
            </div>
            <button
              onClick={next}
              disabled={activeColIndex === columns.length - 1}
              className={cn(
                "p-1 rounded-full",
                activeColIndex === columns.length - 1 && "opacity-30",
              )}
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* Single active column full-width */}
          <div className="flex-1 min-h-0 px-4 pb-4 flex flex-col">
            {activeCol && (
              <KanbanColumn
                column={activeCol}
                filterMemberId={filterMemberId}
                onTaskClick={setSelectedTaskId}
              />
            )}
          </div>
        </>
      )}

      <TaskDetailSheet
        taskId={selectedTaskId}
        onClose={() => setSelectedTaskId(null)}
      />
      <CreateTaskSheet open={createOpen} onClose={() => setCreateOpen(false)} />
    </div>
  );
}
