"use client";

import { BarChart3, BookOpenCheck, Check, ClipboardCheck, FolderInput, FolderMinus, FolderPlus, Import, Library, MessageSquarePlus, MoreHorizontal, Pencil, Search, Settings, Trash2, Upload, X } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Button, Input } from "./ui";

type Chat = { id: string; title: string; updated_at: string; project_id?: string | null; imported_from_provider?: string | null; imported_at?: string | null };
type Project = { id: string; name: string; description?: string; color?: string; chat_count?: number; imported_from_provider?: string | null; import_inferred?: boolean };

function distinctChats(chats: Chat[]) {
  const seen = new Set<string>();
  return chats.filter((chat) => {
    const key = chat.title.trim().replace(/\s+/g, " ").toLowerCase() || chat.id;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function Sidebar({
  allChats,
  projects,
  activeChatId,
  activeProjectId,
  creatingProject,
  projectName,
  onProjectNameChange,
  onCreateProject,
  onCancelProjectCreate,
  onSelectProject,
  onNewChat,
  onRenameChat,
  onMoveChat,
  onDeleteChat
}: {
  allChats: Chat[];
  projects: Project[];
  activeChatId?: string;
  activeProjectId?: string;
  creatingProject: boolean;
  projectName: string;
  onProjectNameChange: (value: string) => void;
  onCreateProject: (chatIds?: string[]) => void;
  onCancelProjectCreate: () => void;
  onSelectProject: (projectId?: string) => void;
  onNewChat?: () => void;
  onRenameChat: (chatId: string, title: string) => void;
  onMoveChat: (chatId: string, projectId?: string) => void;
  onDeleteChat: (chatId: string) => void;
}) {
  const [openMenuId, setOpenMenuId] = useState<string | null>(null);
  const [renamingChatId, setRenamingChatId] = useState<string | null>(null);
  const [renameDraft, setRenameDraft] = useState("");
  const [movingChatId, setMovingChatId] = useState<string | null>(null);
  const [selectedProjectChatIds, setSelectedProjectChatIds] = useState<string[]>([]);
  const [chatSearch, setChatSearch] = useState("");
  const sidebarRef = useRef<HTMLElement | null>(null);
  const distinctAllChats = distinctChats(allChats);
  const projectAttachChats = distinctAllChats.slice(0, 8);
  const normalizedChatSearch = chatSearch.trim().toLowerCase();
  const visibleChatList = normalizedChatSearch
    ? distinctAllChats.filter((chat) => chat.title.toLowerCase().includes(normalizedChatSearch))
    : distinctAllChats;

  function projectDistinctCount(projectId: string) {
    return distinctChats(allChats.filter((chat) => chat.project_id === projectId)).length;
  }

  function closeChatMenus() {
    setOpenMenuId(null);
    setMovingChatId(null);
  }

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!sidebarRef.current?.contains(event.target as Node)) {
        closeChatMenus();
        setRenamingChatId(null);
      }
    }

    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeChatMenus();
        setRenamingChatId(null);
      }
    }

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  function startRename(chat: Chat) {
    setRenamingChatId(chat.id);
    setRenameDraft(chat.title);
    setMovingChatId(null);
  }

  function submitRename(chatId: string) {
    const title = renameDraft.trim();
    if (!title) return;
    onRenameChat(chatId, title);
    setRenamingChatId(null);
    setOpenMenuId(null);
  }

  function toggleProjectChat(chatId: string) {
    setSelectedProjectChatIds((current) =>
      current.includes(chatId) ? current.filter((id) => id !== chatId) : [...current, chatId]
    );
  }

  function submitProjectCreate() {
    onCreateProject(selectedProjectChatIds);
    setSelectedProjectChatIds([]);
  }

  function closeProjectCreate() {
    setSelectedProjectChatIds([]);
    onCancelProjectCreate();
  }

  function renderChatRows(chatList: Chat[], emptyText: string, nested = false) {
    return (
      <div className={`grid gap-1 ${nested ? "border-l border-white/10 pl-2" : ""}`}>
        {chatList.length === 0 ? (
          <div className="px-3 py-2 text-xs text-white/48">{emptyText}</div>
        ) : chatList.map((chat) => (
          <div
            key={chat.id}
            className="relative min-w-0"
            data-chat-row={chat.id}
            onMouseLeave={() => {
              if (openMenuId === chat.id && renamingChatId !== chat.id) closeChatMenus();
            }}
          >
            {renamingChatId === chat.id ? (
              <div className="rounded-lg bg-white/10 p-1.5">
                <Input
                  autoFocus
                  aria-label={`Rename ${chat.title}`}
                  className="h-8 w-full min-w-0 border-white/15 bg-white/10 text-xs text-white placeholder:text-white/45"
                  value={renameDraft}
                  onChange={(event) => setRenameDraft(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") submitRename(chat.id);
                    if (event.key === "Escape") {
                      setRenamingChatId(null);
                      closeChatMenus();
                    }
                  }}
                />
                <div className="mt-1 flex justify-end gap-1">
                  <Button aria-label="Save chat name" className="h-7 w-7 border-white/12 bg-white/10 p-0 text-white" onClick={() => submitRename(chat.id)} title="Save chat name">
                    <Check size={13} />
                  </Button>
                  <Button aria-label="Cancel renaming" className="h-7 w-7 border-white/12 bg-white/10 p-0 text-white" onClick={() => setRenamingChatId(null)} title="Cancel renaming">
                    <X size={13} />
                  </Button>
                </div>
              </div>
            ) : (
              <div className={`group relative flex h-9 min-w-0 items-center overflow-hidden rounded-lg pr-9 transition hover:bg-white/10 ${activeChatId === chat.id ? "bg-white/12 text-white" : "text-white/72"}`}>
                <Link
                  className="block h-9 min-w-0 flex-1 truncate px-3 py-2 text-sm leading-5"
                  href={`/?chat=${chat.id}${chat.project_id ? `&project=${chat.project_id}` : ""}`}
                  onClick={closeChatMenus}
                  title={chat.title}
                >
                  <span className="flex min-w-0 items-center gap-1.5">
                    <span className="truncate">{chat.title}</span>
                    {chat.imported_from_provider ? <span className="shrink-0 rounded-full bg-white/10 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-white/45">Imported</span> : null}
                  </span>
                </Link>
                <button
                  aria-label={`Actions for ${chat.title}`}
                  className="absolute right-1 top-1 grid h-7 w-7 shrink-0 place-items-center rounded-md bg-[hsl(var(--sidebar))]/80 text-white/60 opacity-100 backdrop-blur transition hover:bg-white/10 hover:text-white sm:opacity-0 sm:group-hover:opacity-100"
                  onClick={(event) => {
                    const row = event.currentTarget.closest(`[data-chat-row="${chat.id}"]`);
                    setOpenMenuId(openMenuId === chat.id ? null : chat.id);
                    setMovingChatId(null);
                    window.requestAnimationFrame(() => {
                      window.requestAnimationFrame(() => row?.scrollIntoView({ block: "nearest" }));
                    });
                  }}
                  title={`Actions for ${chat.title}`}
                  type="button"
                >
                  <MoreHorizontal size={15} />
                </button>
              </div>
            )}

            {openMenuId === chat.id && renamingChatId !== chat.id ? (
              <div className="sidebar-popover relative z-30 mx-1 mt-1 rounded-xl border border-white/12 p-1.5 text-sm text-white shadow-2xl" role="menu" aria-label={`Chat menu for ${chat.title}`}>
                <button className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left hover:bg-white/10" onClick={() => startRename(chat)} role="menuitem" type="button">
                  <Pencil size={14} /> Rename
                </button>
                <button className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left hover:bg-white/10" onClick={() => setMovingChatId(movingChatId === chat.id ? null : chat.id)} role="menuitem" type="button">
                  <FolderInput size={14} /> Add to project
                </button>
                {chat.project_id ? (
                  <button
                    className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left hover:bg-white/10"
                    onClick={() => {
                      onMoveChat(chat.id, undefined);
                      setOpenMenuId(null);
                    }}
                    role="menuitem"
                    type="button"
                  >
                    <FolderMinus size={14} /> Remove project
                  </button>
                ) : null}
                <button
                  className="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-left text-red-200 hover:bg-red-500/15"
                  onClick={() => {
                    onDeleteChat(chat.id);
                    setOpenMenuId(null);
                  }}
                  role="menuitem"
                  type="button"
                >
                  <Trash2 size={14} /> Delete
                </button>

                {movingChatId === chat.id ? (
                  <div className="mt-1 border-t border-white/10 pt-1">
                    {projects.length === 0 ? (
                      <div className="px-2.5 py-2 text-xs text-white/50">No projects yet.</div>
                    ) : projects.map((project) => (
                      <button
                        key={project.id}
                        className="flex w-full items-center justify-between gap-2 rounded-lg px-2.5 py-2 text-left text-xs hover:bg-white/10"
                        onClick={() => {
                          onMoveChat(chat.id, project.id);
                          setMovingChatId(null);
                          setOpenMenuId(null);
                        }}
                        type="button"
                      >
                        <span className="truncate">{project.name}</span>
                        {chat.project_id === project.id ? <Check size={13} /> : null}
                      </button>
                    ))}
                  </div>
                ) : null}
              </div>
            ) : null}
          </div>
        ))}
      </div>
    );
  }

  return (
    <aside ref={sidebarRef} className="sidebar-surface flex h-dvh w-[calc(100vw-2.5rem)] max-w-80 shrink-0 flex-col overflow-hidden border-r border-white/10 lg:w-80" aria-label="Chats and projects">
      <div className="shrink-0 p-4">
        <div className="mb-4 flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl border border-white/15 bg-white/10 shadow-inner">
            <BookOpenCheck size={20} />
          </div>
          <div>
            <div className="text-sm font-semibold">Muslim LLM</div>
            <div className="text-xs text-white/58">Grounded AI</div>
          </div>
        </div>
        <div>
          <Button className="w-full border-white/12 bg-white/10 text-white hover:bg-white/15" onClick={onNewChat}>
            <MessageSquarePlus size={16} /> New chat
          </Button>
        </div>
      </div>

      <div className="flex max-h-[42dvh] shrink-0 flex-col overflow-hidden border-y border-white/10 px-3 py-3">
        <div className="mb-2 flex items-center justify-between px-3">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-white/45">
            <Library size={13} /> Projects
          </div>
          <div className="flex items-center gap-1.5">
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] text-white/45">{projects.length}</span>
            <button
              aria-label="Create a new project"
              className="grid h-6 w-6 place-items-center rounded-md text-white/55 transition hover:bg-white/10 hover:text-white"
              onClick={() => onCreateProject(selectedProjectChatIds)}
              title="New project"
              type="button"
            >
              <FolderPlus size={14} />
            </button>
          </div>
        </div>
        {creatingProject ? (
          <div className="mb-2 rounded-xl border border-white/12 bg-black/18 p-2">
            <div className="mb-2 flex items-center justify-between gap-2 px-1">
              <div className="text-[11px] font-semibold uppercase tracking-wide text-white/45">New project</div>
              <button
                aria-label="Close new project"
                className="grid h-6 w-6 place-items-center rounded-md text-white/55 transition hover:bg-white/10 hover:text-white"
                onClick={closeProjectCreate}
                title="Close"
                type="button"
              >
                <X size={14} />
              </button>
            </div>
            <Input
              autoFocus
              aria-label="Project name"
              className="border-white/15 bg-white/10 text-white placeholder:text-white/45"
              value={projectName}
              onChange={(event) => onProjectNameChange(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") submitProjectCreate();
                if (event.key === "Escape") closeProjectCreate();
              }}
              placeholder="Project name"
            />
            <div className="my-2 border-t border-white/10" />
            <div className="mb-1 px-1 text-[11px] font-semibold uppercase tracking-wide text-white/45">Add chats</div>
            <div className="grid max-h-40 gap-1 overflow-y-auto">
              {projectAttachChats.length === 0 ? (
                <div className="px-1 py-1 text-xs text-white/45">No chats yet.</div>
              ) : projectAttachChats.map((chat) => (
                <label key={chat.id} className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-white/70 hover:bg-white/10">
                  <input
                    className="h-3.5 w-3.5 accent-[hsl(var(--primary))]"
                    type="checkbox"
                    checked={selectedProjectChatIds.includes(chat.id)}
                    onChange={() => toggleProjectChat(chat.id)}
                  />
                  <span className="truncate">{chat.title}</span>
                </label>
              ))}
            </div>
            <Button className="mt-2 h-8 w-full border-white/12 bg-white/10 text-xs text-white hover:bg-white/15" onClick={submitProjectCreate}>
              Create project
            </Button>
          </div>
        ) : null}
        <div className="grid max-h-44 shrink-0 gap-1 overflow-y-auto">
          {projects.length === 0 ? (
            <div className="px-3 py-2 text-xs text-white/48">No projects yet.</div>
          ) : projects.map((project) => (
            <div key={project.id} className="min-w-0">
              <button
                aria-label={`Open project ${project.name}`}
                className={`flex w-full items-center justify-between gap-2 rounded-lg px-3 py-2 text-left text-sm transition hover:bg-white/10 ${activeProjectId === project.id ? "bg-white/12 text-white" : "text-white/72"}`}
                onClick={() => {
                  closeChatMenus();
                  onSelectProject(project.id);
                }}
                type="button"
              >
                <span className="min-w-0 flex items-center gap-2">
                  <FolderPlus size={14} className="shrink-0 opacity-70" />
                  <span className="truncate">{project.name}</span>
                  {project.imported_from_provider ? <span className="rounded-full bg-white/10 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-white/45">{project.import_inferred ? "Inferred" : "Imported"}</span> : null}
                </span>
                <span className="shrink-0 rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-white/55">{projectDistinctCount(project.id)}</span>
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col px-3 py-3">
        <div className="mb-2 flex items-center justify-between px-3">
          <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-wide text-white/45">
            <MessageSquarePlus size={13} /> All chats
          </div>
          <span className="rounded-full bg-white/10 px-2 py-0.5 text-[10px] text-white/45">{distinctAllChats.length}</span>
        </div>
        <div className="mb-2 px-1">
          <div className="flex h-9 items-center gap-2 rounded-lg border border-white/10 bg-white/[0.06] px-2.5 text-white/70 focus-within:border-white/20 focus-within:bg-white/[0.08]">
            <Search size={14} className="shrink-0 text-white/45" />
            <input
              aria-label="Search all chats"
              className="h-full min-w-0 flex-1 bg-transparent text-sm text-white outline-none placeholder:text-white/38"
              value={chatSearch}
              onChange={(event) => setChatSearch(event.target.value)}
              placeholder="Search all chats"
            />
            {chatSearch ? (
              <button
                aria-label="Clear chat search"
                className="grid h-6 w-6 place-items-center rounded-md text-white/45 transition hover:bg-white/10 hover:text-white"
                onClick={() => setChatSearch("")}
                title="Clear search"
                type="button"
              >
                <X size={13} />
              </button>
            ) : null}
          </div>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto">
          {renderChatRows(visibleChatList, normalizedChatSearch ? "No matching chats." : "No chats yet.")}
        </div>
      </div>

      <nav className="relative z-20 grid shrink-0 grid-cols-2 gap-1 border-t border-white/10 bg-[hsl(var(--sidebar))] p-3 text-xs min-[900px]:grid-cols-1 min-[900px]:text-sm" aria-label="Workspace tools">
        <Link className="flex min-w-0 items-center gap-2 rounded-lg px-2.5 py-2 text-white/70 hover:bg-white/10 hover:text-white" href="/sources"><Search className="shrink-0" size={16} /> Sources</Link>
        <Link className="flex min-w-0 items-center gap-2 rounded-lg px-2.5 py-2 text-white/70 hover:bg-white/10 hover:text-white" href="/admin"><Upload className="shrink-0" size={16} /> Documents</Link>
        <Link className="flex min-w-0 items-center gap-2 rounded-lg px-2.5 py-2 text-white/70 hover:bg-white/10 hover:text-white" href="/evals-dashboard"><BarChart3 className="shrink-0" size={16} /> Evals</Link>
        <Link className="flex min-w-0 items-center gap-2 rounded-lg px-2.5 py-2 text-white/70 hover:bg-white/10 hover:text-white" href="/eval"><ClipboardCheck className="shrink-0" size={16} /> Evaluation</Link>
        <Link className="flex min-w-0 items-center gap-2 rounded-lg px-2.5 py-2 text-white/70 hover:bg-white/10 hover:text-white" href="/context-sync"><Import className="shrink-0" size={16} /> Context Sync</Link>
        <Link className="flex min-w-0 items-center gap-2 rounded-lg px-2.5 py-2 text-white/70 hover:bg-white/10 hover:text-white" href="/settings"><Settings className="shrink-0" size={16} /> Settings</Link>
      </nav>
    </aside>
  );
}
