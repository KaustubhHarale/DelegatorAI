import React, { useEffect, useMemo, useState } from "react";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  Bell,
  Bot,
  Check,
  CheckCheck,
  CircleHelp,
  Clock3,
  Eye,
  EyeOff,
  FileText,
  LayoutDashboard,
  ListTodo,
  LockKeyhole,
  Mail,
  MessageCircle,
  Plus,
  Search,
  Send,
  Settings2,
  ShieldCheck,
  Sparkles,
  Users,
  X,
} from "lucide-react";
import { api } from "./api";
import LandingPage from "./components/landing/LandingPage.jsx";

const statusFromApi = {
  Pending: "To do",
  "In Progress": "In progress",
  Blocked: "Blocked",
  Complete: "Completed",
};
const statusToApi = {
  "To do": "Pending",
  "In progress": "In Progress",
  Blocked: "Blocked",
  Completed: "Complete",
};

function initials(name = "") {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "?";
}

function fromApiTask(task) {
  return {
    id: task.id,
    title: task.title,
    project: task.project_id,
    ownerId: task.owner_id,
    assignee: task.assignee,
    initials: task.initials || initials(task.assignee),
    due: task.deadline
      ? new Date(`${task.deadline}T00:00:00`).toLocaleDateString(undefined, { month: "short", day: "numeric" })
      : "No deadline",
    deadline: task.deadline,
    description: task.description,
    status: statusFromApi[task.status] || task.status,
    blocker: task.blocker,
    progress: task.progress,
  };
}

function defaultDeadline() {
  const date = new Date();
  date.setDate(date.getDate() + 7);
  return date.toISOString().slice(0, 10);
}

function TaskTable({ tasks, onStatusClick, disabled, emptyMessage = "No tasks found." }) {
  if (tasks.length === 0) return <p className="no-tasks">{emptyMessage}</p>;
  return (
    <div className="task-table-scroll">
      <table className="workspace-task-table">
        <thead><tr><th>TASK NAME</th><th>ASSIGNEE</th><th>DUE DATE</th><th>STATUS</th></tr></thead>
        <tbody>
          {tasks.map((task) => (
            <tr key={task.id}>
              <td>
                <div className="workspace-task-name">
                  <button
                    className={`task-check ${task.status === "Completed" ? "checked" : ""}`}
                    onClick={() => onStatusClick(task)}
                    disabled={disabled || task.status === "Completed"}
                    aria-label={`Complete ${task.title}`}
                  >{task.status === "Completed" && <Check size={12} />}</button>
                  <div><strong className={task.status === "Completed" ? "task-completed" : ""}>{task.title}</strong><small>{task.project}</small></div>
                </div>
              </td>
              <td><span className="assignee"><span className="avatar">{task.initials}</span>{task.assignee}</span></td>
              <td>{task.due}</td>
              <td><button className={`task-status ${task.status.toLowerCase().replace(" ", "-")}`} onClick={() => onStatusClick(task)} disabled={disabled || task.status === "Completed"}>{task.status}</button></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function LoginPage({ onSignIn, onExplore }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  return (
    <main className="auth-page">
      <section className="auth-showcase">
        <a className="auth-brand" href="#login" aria-label="DelegatorAI home">
          <span className="auth-brand-mark"><Sparkles size={19} /></span>
          <span>Delegator<span>AI</span></span>
        </a>
        <div className="auth-message">
          <span className="auth-eyebrow"><span className="live-dot" /> YOUR TEAM, IN SYNC</span>
          <h1>Good work happens<br />when teams flow.</h1>
          <p>Bring your projects, people, and priorities together in one clear space.</p>
        </div>
        <div className="auth-preview">
          <div className="auth-preview-top"><span>THIS WEEK</span><span>68% complete</span></div>
          <div className="auth-preview-task"><Check size={15} /><div><strong>Design onboarding flow</strong><small>DelegatorAI · Due today</small></div><span>In progress</span></div>
          <div className="auth-progress"><span /></div>
          <div className="auth-preview-bottom"><span className="avatar">AK</span><span className="avatar">HT</span><span className="avatar">RS</span><small>Small team. Big momentum.</small></div>
        </div>
        <button className="auth-explore" type="button" onClick={onExplore}>Explore the product <ArrowRight size={15} /></button>
      </section>

      <section className="auth-panel">
        <form className="auth-card" onSubmit={(event) => { event.preventDefault(); onSignIn(); }}>
          <span className="auth-form-eyebrow">WELCOME BACK</span>
          <h2>Sign in to your workspace</h2>
          <p className="auth-subtitle">Pick up where you and your team left off.</p>

          <label htmlFor="email">Email address</label>
          <div className="auth-input"><Mail size={17} /><input id="email" type="email" autoComplete="email" placeholder="you@company.com" value={email} onChange={(event) => setEmail(event.target.value)} required /></div>
          <div className="auth-password-label"><label htmlFor="password">Password</label><span>Forgot password?</span></div>
          <div className="auth-input"><LockKeyhole size={17} /><input id="password" type={showPassword ? "text" : "password"} autoComplete="current-password" placeholder="Enter your password" value={password} onChange={(event) => setPassword(event.target.value)} required /><button className="password-toggle" type="button" onClick={() => setShowPassword((visible) => !visible)} aria-label={showPassword ? "Hide password" : "Show password"}>{showPassword ? <EyeOff size={17} /> : <Eye size={17} />}</button></div>
          <label className="remember-label"><input type="checkbox" defaultChecked /> Keep me signed in</label>
          <button className="button-primary auth-submit" type="submit">Sign in to workspace <ArrowRight size={16} /></button>
          <button className="auth-demo" type="button" onClick={() => { setEmail("you@delegator.ai"); setPassword("delegator-demo"); }}>Use demo account</button>
          <p className="auth-disclaimer"><ShieldCheck size={14} /> Demo sign-in only. Authentication is not connected.</p>
          <p className="auth-legal">By continuing, you agree to our Terms and Privacy Policy.</p>
        </form>
      </section>
    </main>
  );
}

function Workspace({ onSignOut }) {
  const [tasks, setTasks] = useState([]);
  const [participants, setParticipants] = useState([]);
  const [activity, setActivity] = useState([]);
  const [apiState, setApiState] = useState("loading");
  const [workspaceError, setWorkspaceError] = useState("");
  const [query, setQuery] = useState("");
  const [activePage, setActivePage] = useState("Overview");
  const [statusFilter, setStatusFilter] = useState("All tasks");
  const [projectFilter, setProjectFilter] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newTask, setNewTask] = useState({
    title: "",
    description: "",
    projectId: "college-app",
    ownerId: "",
    deadline: defaultDeadline(),
  });
  const [taskSaving, setTaskSaving] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([api.getTasks(), api.getParticipants()])
      .then(([taskList, participantList]) => {
        if (!active) return;
        setTasks(taskList.map(fromApiTask));
        setParticipants(participantList);
        setApiState("connected");
        Promise.all(taskList.map(async (task) => (
          (await api.getTaskHistory(task.id)).map((entry) => ({
            ...entry,
            taskTitle: task.title,
          }))
        )))
          .then((historyLists) => {
            if (active) {
              setActivity(historyLists.flat().sort((a, b) => new Date(b.time) - new Date(a.time)));
            }
          })
          .catch((error) => {
            if (active) setWorkspaceError(`Could not load activity: ${error.message}`);
          });
      })
      .catch((error) => {
        if (!active) return;
        setWorkspaceError(`Could not load workspace data: ${error.message}`);
        setApiState("error");
      });
    return () => { active = false; };
  }, []);

  const completed = tasks.filter((task) => task.status === "Completed").length;
  const inProgress = tasks.filter((task) => task.status === "In progress").length;
  const visibleTasks = useMemo(
    () => tasks.filter((task) => {
      const matchesQuery = `${task.title} ${task.project} ${task.assignee}`.toLowerCase().includes(query.toLowerCase());
      const matchesProject = !projectFilter || task.project === projectFilter;
      const matchesStatus = statusFilter === "All tasks"
        || (statusFilter === "Open" && task.status !== "Completed")
        || task.status === statusFilter;
      return matchesQuery && matchesProject && matchesStatus;
    }),
    [tasks, query, statusFilter, projectFilter],
  );
  const cycleTask = async (task) => {
    if (apiState !== "connected" || task.status === "Completed") return;
    const nextStatus = task.status === "To do" || task.status === "Blocked" ? "In progress" : "Completed";
    setWorkspaceError("");
    try {
      const updated = await api.updateTask(task.id, { status: statusToApi[nextStatus] });
      setTasks((current) => current.map((item) => item.id === task.id ? fromApiTask(updated) : item));
    } catch (error) {
      setWorkspaceError(`Could not update task: ${error.message}`);
    }
  };
  const createTask = async (event) => {
    event.preventDefault();
    if (!newTask.title.trim() || !newTask.ownerId || apiState !== "connected") return;
    setTaskSaving(true);
    setWorkspaceError("");
    try {
      const created = await api.createTask({
        title: newTask.title.trim(),
        project_id: newTask.projectId,
        owner_id: newTask.ownerId,
        deadline: newTask.deadline,
        description: newTask.description.trim() || newTask.title.trim(),
        priority: "Medium",
      });
      setTasks((current) => [fromApiTask(created), ...current]);
      setNewTask({
        title: "",
        description: "",
        projectId: created.project_id,
        ownerId: "",
        deadline: defaultDeadline(),
      });
      setShowCreate(false);
    } catch (error) {
      setWorkspaceError(`Could not create task: ${error.message}`);
    } finally {
      setTaskSaving(false);
    }
  };
  const openCreateTask = () => {
    setNewTask((current) => ({
      ...current,
      projectId: current.projectId || tasks[0]?.project || "college-app",
      ownerId: current.ownerId || participants[0]?.id || "",
    }));
    setWorkspaceError("");
    setShowCreate(true);
  };
  const projects = useMemo(
    () => [...new Set(tasks.map((task) => task.project).filter(Boolean))].sort(),
    [tasks],
  );
  const pageDescriptions = {
    Overview: "Here’s what’s happening with your team today.",
    "My Tasks": "Browse, filter, and update tasks across your workspace.",
    Projects: "See work grouped by the project it belongs to.",
    Team: "Review participants and the work assigned to each person.",
  };
  const navigate = (page) => {
    setActivePage(page);
    setProjectFilter("");
    setStatusFilter("All tasks");
  };

  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar">
        <a className="workspace-brand" href="#workspace"><span className="auth-brand-mark"><Sparkles size={18} /></span><span>Delegator<span>AI</span></span></a>
        <div className="workspace-label">WORKSPACE</div>
        <button className={`workspace-nav ${activePage === "Overview" ? "active" : ""}`} onClick={() => navigate("Overview")} aria-current={activePage === "Overview" ? "page" : undefined}><LayoutDashboard size={17} /> Overview</button>
        <button className={`workspace-nav ${activePage === "My Tasks" ? "active" : ""}`} onClick={() => navigate("My Tasks")} aria-current={activePage === "My Tasks" ? "page" : undefined}><ListTodo size={17} /> My tasks <span className="nav-count">{tasks.filter((task) => task.status !== "Completed").length}</span></button>
        <button className={`workspace-nav ${activePage === "Projects" ? "active" : ""}`} onClick={() => navigate("Projects")} aria-current={activePage === "Projects" ? "page" : undefined}><FileText size={17} /> Projects</button>
        <button className={`workspace-nav ${activePage === "Team" ? "active" : ""}`} onClick={() => navigate("Team")} aria-current={activePage === "Team" ? "page" : undefined}><Users size={17} /> Team</button>
        <div className="workspace-sidebar-bottom">
          <button className="workspace-nav"><CircleHelp size={17} /> Help & support</button>
          <button className="workspace-nav"><Settings2 size={17} /> Settings</button>
          <button className="signed-in-user" onClick={onSignOut}><span className="avatar">KA</span><span><strong>Kaustubh</strong><small>Sign out</small></span><ArrowUpRight size={15} /></button>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <div className="breadcrumbs">Workspace <span>/</span> <strong>{activePage}</strong></div>
          <div className="workspace-top-actions">
            <label className="workspace-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tasks..." /></label>
            <button className="square-button" aria-label="Notifications"><Bell size={17} /></button>
            <span className={`backend-state ${apiState}`} aria-live="polite">
              {apiState === "loading" ? "Connecting…" : apiState === "connected" ? "Backend connected" : "Backend unavailable"}
            </span>
          </div>
        </header>

        <div className="workspace-content">
          <section className="workspace-welcome">
            <div><span className="auth-form-eyebrow">DELEGATORAI WORKSPACE</span><h1>{activePage}</h1><p>{pageDescriptions[activePage]}</p></div>
            <button className="button-primary create-task-button" onClick={openCreateTask} disabled={apiState !== "connected" || participants.length === 0}><Plus size={16} /> Create task</button>
          </section>
          {workspaceError && <p className="workspace-error" role="alert">{workspaceError}</p>}
          {apiState === "connected" && participants.length === 0 && (
            <p className="workspace-empty-info">
              The backend is reachable, but this database has no participants yet.
              Run <code>python seed.py</code> in the project folder to add sample
              participants and tasks; seeding keeps existing records.
            </p>
          )}

          {activePage === "Overview" ? (
            <>
          <section className="workspace-panel task-overview">
            <div className="workspace-panel-heading"><div><h2>Task overview</h2><p>Keep track of what your team is working on.</p></div><span className="panel-count">{tasks.length} tasks</span></div>
            <TaskTable tasks={visibleTasks.slice(0, 6)} onStatusClick={cycleTask} disabled={apiState !== "connected"} emptyMessage="No tasks match your search." />
            <div className="workspace-panel-footer">Showing {visibleTasks.length} of {tasks.length} tasks <button onClick={openCreateTask} disabled={apiState !== "connected" || participants.length === 0}>Add a task <ArrowRight size={14} /></button></div>
          </section>

          <section className="workspace-panel members-panel">
            <div className="workspace-panel-heading"><div><h2>Team members</h2><p>{participants.length} people in your workspace</p></div><span className="text-button"><Users size={15} /> Team</span></div>
            <div className="member-list">{participants.map((member) => <div className="member-row" key={member.id}><span className="avatar">{initials(member.name)}</span><span className="member-info"><strong>{member.name}</strong><small>{member.email || "Workspace member"}</small></span><span className="member-status online">Member</span></div>)}{participants.length === 0 && <p className="no-tasks">No participants are configured yet.</p>}</div>
          </section>

          <section className="workspace-stats" aria-label="Workspace statistics">
            <MetricCard icon={<ListTodo size={17} />} label="Total tasks" value={String(tasks.length).padStart(2, "0")} note="Across all projects" />
            <MetricCard icon={<Activity size={17} />} label="In progress" value={String(inProgress).padStart(2, "0")} note="Work underway" />
            <MetricCard icon={<CheckCheck size={17} />} label="Completed" value={String(completed).padStart(2, "0")} note="Nice work, team!" />
            <MetricCard icon={<Clock3 size={17} />} label="Open tasks" value={String(tasks.length - completed).padStart(2, "0")} note="Still need attention" />
          </section>

          <section className="workspace-lower-grid">
            <div className="workspace-panel progress-panel">
              <div className="workspace-panel-heading"><div><h2>Project progress</h2><p>Across your workspace</p></div><ArrowUpRight size={16} /></div>
              <div className="progress-content"><div className="progress-ring" style={{ "--progress": `${tasks.length ? completed / tasks.length * 100 : 0}%` }}><strong>{tasks.length ? Math.round(completed / tasks.length * 100) : 0}%</strong><small>complete</small></div><div className="progress-legend"><span><i className="legend-complete" /> Completed <strong>{completed}</strong></span><span><i className="legend-progress" /> In progress <strong>{inProgress}</strong></span><span><i className="legend-todo" /> To do <strong>{tasks.length - completed - inProgress}</strong></span></div></div>
            </div>
            <div className="workspace-panel activity-panel"><div className="workspace-panel-heading"><div><h2>Recent activity</h2><p>Persisted task updates and messages.</p></div><Activity size={17} /></div><div className="activity-list">{activity.slice(0, 8).map((entry) => <p key={entry.id}><Activity size={15} /><span><strong>{entry.title}</strong> {entry.taskTitle}: {entry.detail}<small>{new Date(entry.time).toLocaleString()}</small></span></p>)}{activity.length === 0 && <p className="no-tasks">No recorded task activity yet.</p>}</div></div>
          </section>
          <CoordinatorChat connected={apiState === "connected"} />
            </>
          ) : activePage === "My Tasks" ? (
            <>
              <section className="workspace-panel page-panel">
                <div className="workspace-panel-heading"><div><h2>All tasks</h2><p>{visibleTasks.length} tasks shown</p></div><span className="panel-count">{tasks.length} total</span></div>
                <div className="page-filters" role="group" aria-label="Filter tasks by status">
                  {["All tasks", "Open", "To do", "In progress", "Blocked", "Completed"].map((filter) => (
                    <button key={filter} className={`filter-chip ${statusFilter === filter ? "selected" : ""}`} onClick={() => setStatusFilter(filter)}>{filter}</button>
                  ))}
                </div>
                <TaskTable tasks={visibleTasks} onStatusClick={cycleTask} disabled={apiState !== "connected"} emptyMessage="No tasks match this filter." />
              </section>
              <CoordinatorChat connected={apiState === "connected"} />
            </>
          ) : activePage === "Projects" ? (
            <section className="page-card-grid" aria-label="Projects">
              {projects.map((project) => {
                const projectTasks = tasks.filter((task) => task.project === project);
                const projectComplete = projectTasks.filter((task) => task.status === "Completed").length;
                const percent = projectTasks.length ? Math.round(projectComplete / projectTasks.length * 100) : 0;
                return (
                  <article className="workspace-panel project-card" key={project}>
                    <div className="project-card-mark"><FileText size={19} /></div>
                    <span className="auth-form-eyebrow">PROJECT</span>
                    <h2>{project}</h2>
                    <p>{projectTasks.length} {projectTasks.length === 1 ? "task" : "tasks"} · {projectComplete} completed</p>
                    <div className="project-progress-track"><span style={{ width: `${percent}%` }} /></div>
                    <div className="project-card-footer"><span>{percent}% complete</span><button onClick={() => { setProjectFilter(project); setStatusFilter("All tasks"); setQuery(""); setActivePage("My Tasks"); }}>View tasks <ArrowRight size={14} /></button></div>
                  </article>
                );
              })}
              {projects.length === 0 && <section className="workspace-panel"><p className="no-tasks">No projects yet. Create a task to start a project.</p></section>}
            </section>
          ) : (
            <section className="workspace-panel page-panel">
              <div className="workspace-panel-heading"><div><h2>Workspace members</h2><p>{participants.length} registered participants</p></div><span className="panel-count">{participants.length} members</span></div>
              <div className="team-directory">
                {participants.map((member) => {
                  const ownedTasks = tasks.filter((task) => task.ownerId === member.id);
                  const openTasks = ownedTasks.filter((task) => task.status !== "Completed").length;
                  return (
                    <article className="team-member-card" key={member.id}>
                      <span className="avatar">{initials(member.name)}</span>
                      <div className="team-member-details"><h3>{member.name}</h3><p>{member.email || "Workspace member"}</p><small>{ownedTasks.length} assigned · {openTasks} open</small></div>
                      <button className="text-button" onClick={() => { setQuery(member.name); setProjectFilter(""); setStatusFilter("All tasks"); setActivePage("My Tasks"); }}>View tasks <ArrowRight size={14} /></button>
                    </article>
                  );
                })}
              </div>
              {participants.length === 0 && <p className="no-tasks">No team members are configured in the backend yet.</p>}
            </section>
          )}
        </div>
      </main>

      {showCreate && <div className="modal-backdrop" onClick={() => !taskSaving && setShowCreate(false)}><form className="create-modal" onSubmit={createTask} onClick={(event) => event.stopPropagation()}><div className="modal-title"><div><h2>Create a task</h2><p>Add work to your team’s queue.</p></div><button type="button" className="square-button" onClick={() => setShowCreate(false)} aria-label="Close" disabled={taskSaving}><X size={17} /></button></div><label htmlFor="new-task">Task name</label><input id="new-task" autoFocus maxLength={300} value={newTask.title} onChange={(event) => setNewTask((current) => ({ ...current, title: event.target.value }))} placeholder="e.g. Review API integration" required /><label htmlFor="task-description">Description</label><textarea id="task-description" maxLength={2000} value={newTask.description} onChange={(event) => setNewTask((current) => ({ ...current, description: event.target.value }))} placeholder="What does done look like?" rows="3" /><label htmlFor="task-project">Project</label><select id="task-project" value={newTask.projectId} onChange={(event) => setNewTask((current) => ({ ...current, projectId: event.target.value }))} required>{[...new Set([...tasks.map((task) => task.project), newTask.projectId].filter(Boolean))].map((project) => <option key={project} value={project}>{project}</option>)}</select><label htmlFor="task-owner">Assignee</label><select id="task-owner" value={newTask.ownerId} onChange={(event) => setNewTask((current) => ({ ...current, ownerId: event.target.value }))} required><option value="" disabled>Select a team member</option>{participants.map((person) => <option key={person.id} value={person.id}>{person.name}</option>)}</select><label htmlFor="task-deadline">Deadline</label><input id="task-deadline" type="date" value={newTask.deadline} onChange={(event) => setNewTask((current) => ({ ...current, deadline: event.target.value }))} required /><div className="modal-actions"><button type="button" className="auth-demo" onClick={() => setShowCreate(false)} disabled={taskSaving}>Cancel</button><button className="create-task-button" type="submit" disabled={taskSaving}>{taskSaving ? "Creating…" : <><Plus size={15} /> Create task</>}</button></div></form></div>}
    </div>
  );
}

function CoordinatorChat({ connected }) {
  const [conversation, setConversation] = useState([]);
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const sendMessage = async (event) => {
    event.preventDefault();
    const message = draft.trim();
    if (!message || sending) return;
    const history = conversation.slice(-12);
    setConversation((current) => [...current, { role: "user", content: message }]);
    setDraft("");
    setSending(true);
    setError("");
    try {
      const result = await api.chatWithCoordinator(message, history);
      setConversation((current) => [...current, { role: "assistant", content: result.reply }]);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setSending(false);
    }
  };

  return (
    <section className="workspace-panel coordinator-panel">
      <div className="coordinator-heading">
        <span className="coordinator-icon"><Bot size={19} /></span>
        <div><h2>AI coordinator</h2><p>{connected ? "Ask about your live workspace" : "Waiting for backend connection"}</p></div>
        <span className={`preview-badge ${connected ? "connected" : ""}`}>{connected ? "GPT-OSS-20B" : "OFFLINE"}</span>
      </div>
      <div className="coordinator-chat" aria-live="polite" aria-label="Coordinator conversation">
        {conversation.length === 0 && <p className="coordinator-message"><Sparkles size={15} /> Hi! Ask me about task progress, deadlines, or blockers in your workspace.</p>}
        {conversation.map((turn, index) => (
          <p className={`coordinator-message ${turn.role}`} key={`${turn.role}-${index}`}>
            {turn.role === "assistant" && <Bot size={15} />}
            <span>{turn.content}</span>
          </p>
        ))}
        {sending && <p className="coordinator-typing" role="status">Coordinator is thinking…</p>}
        {error && <p className="coordinator-error" role="alert">Could not get a response: {error}</p>}
      </div>
      <form className="coordinator-input" onSubmit={sendMessage}>
        <input
          aria-label="Message the AI coordinator"
          maxLength={2000}
          placeholder="Ask about tasks, progress, or blockers…"
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          disabled={sending}
        />
        <button type="submit" aria-label="Send message" disabled={!draft.trim() || sending}><Send size={15} /></button>
      </form>
      <small className="coordinator-disclaimer"><ShieldCheck size={13} /> Read-only assistant using current workspace tasks. It cannot change tasks.</small>
    </section>
  );
}

function MetricCard({ icon, label, value, note }) {
  return <article className="metric-card"><div className="metric-heading"><span>{label}</span><span className="metric-icon">{icon}</span></div><strong className="metric-value">{value}</strong><small>{note}</small></article>;
}

export default function App() {
  const [screen, setScreen] = useState("login");
  if (screen === "landing") return <LandingPage onGetStarted={() => setScreen("login")} />;
  if (screen === "workspace") return <Workspace onSignOut={() => setScreen("login")} />;
  return <LoginPage onSignIn={() => setScreen("workspace")} onExplore={() => setScreen("landing")} />;
}
