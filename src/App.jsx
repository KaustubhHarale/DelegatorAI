import { useEffect, useMemo, useState } from "react";
import {
  Activity, AlertCircle, ArrowDownRight, ArrowRight, ArrowUpRight, Bell, Bot, CalendarDays,
  Check, CheckCheck, ChevronDown, ChevronLeft, ChevronRight, CircleHelp, Clock3, Command,
  Filter, LayoutDashboard, ListTodo, Menu, MessageCircle, MoreHorizontal, Plus, Search,
  Send, Settings, ShieldCheck, Sparkles, Users, X, Zap, CircleCheck, CircleDashed,
  CircleDot, PanelLeftClose, SlidersHorizontal, Github, ExternalLink, RefreshCw, ClipboardList
} from "lucide-react";
import { api } from "./api";

const initialTasks = [
  { id: "T-101", title: "Set up authentication API", description: "Create signup/login endpoints and JWT validation.", assignee: "Kabir Mehta", initials: "KM", role: "Backend", status: "In Progress", priority: "High", dueDate: "Oct 18", progress: 65, project: "CampusConnect", updated: "12 min ago", blocker: "" },
  { id: "T-102", title: "Build project dashboard UI", description: "Implement responsive dashboard cards and project overview.", assignee: "Riya Sharma", initials: "RS", role: "Frontend", status: "In Progress", priority: "High", dueDate: "Oct 19", progress: 45, project: "CampusConnect", updated: "24 min ago", blocker: "" },
  { id: "T-103", title: "Create onboarding wireframes", description: "Finalize new user onboarding and invite flow.", assignee: "Arjun Patel", initials: "AP", role: "UI/UX", status: "Completed", priority: "Medium", dueDate: "Oct 16", progress: 100, project: "CampusConnect", updated: "1 hr ago", blocker: "" },
  { id: "T-104", title: "Test invite flow", description: "Validate invitation links and error states.", assignee: "Neha Gupta", initials: "NG", role: "QA", status: "Blocked", priority: "High", dueDate: "Oct 17", progress: 30, project: "CampusConnect", updated: "8 min ago", blocker: "Waiting for the invite endpoint from backend." },
  { id: "T-105", title: "Design database schema", description: "Define users, projects, memberships, tasks and activity log.", assignee: "Kabir Mehta", initials: "KM", role: "Backend", status: "Completed", priority: "Medium", dueDate: "Oct 15", progress: 100, project: "CampusConnect", updated: "Yesterday", blocker: "" },
  { id: "T-106", title: "Connect API to task board", description: "Wire task board to backend endpoints and handle loading states.", assignee: "Riya Sharma", initials: "RS", role: "Frontend", status: "Pending", priority: "Medium", dueDate: "Oct 21", progress: 0, project: "CampusConnect", updated: "Yesterday", blocker: "" },
];

const initialActivity = [
  { id: 1, kind: "success", title: "Task marked as completed", detail: "Arjun completed “Create onboarding wireframes”.", time: "14 min ago" },
  { id: 2, kind: "bot", title: "AI follow-up sent", detail: "Asked Neha for an update on the invite flow blocker.", time: "28 min ago" },
  { id: 3, kind: "warning", title: "Blocker detected", detail: "Neha is waiting for the invite endpoint.", time: "42 min ago" },
  { id: 4, kind: "update", title: "Task progress updated", detail: "Riya moved the dashboard UI to 45%.", time: "1 hr ago" },
];

const navGroups = [
  { label: "WORKSPACE", items: [
    { id: "Overview", icon: LayoutDashboard },
    { id: "Projects", icon: ClipboardList },
    { id: "My Tasks", icon: ListTodo },
    { id: "Team Members", icon: Users },
  ]},
  { label: "INTELLIGENCE", items: [
    { id: "AI Coordinator", icon: Bot, badge: "DEMO" },
    { id: "Activity Log", icon: Activity },
  ]},
];

const statusMeta = {
  "Pending": { className: "pending", icon: CircleDashed },
  "In Progress": { className: "progress", icon: CircleDot },
  "Blocked": { className: "blocked", icon: AlertCircle },
  "Completed": { className: "completed", icon: CircleCheck },
};
const initialPeople = [
  { name: "Aditi Sharma", initials: "AS", role: "Project Lead", tasks: 2, color: "purple", email: "aditi@campusconnect.dev" },
  { name: "Kabir Mehta", initials: "KM", role: "Backend Developer", tasks: 2, color: "blue", email: "kabir@campusconnect.dev" },
  { name: "Riya Sharma", initials: "RS", role: "Frontend Developer", tasks: 2, color: "pink", email: "riya@campusconnect.dev" },
  { name: "Arjun Patel", initials: "AP", role: "UI/UX Designer", tasks: 1, color: "orange", email: "arjun@campusconnect.dev" },
  { name: "Neha Gupta", initials: "NG", role: "QA Engineer", tasks: 1, color: "green", email: "neha@campusconnect.dev" },
];

function Avatar({ initials, color = "blue", size = "normal" }) {
  return <span className={`avatar avatar-${color} avatar-${size}`} aria-hidden="true">{initials}</span>;
}
function StatusPill({ status }) {
  const Meta = statusMeta[status] || statusMeta.Pending;
  const Icon = Meta.icon;
  return <span className={`status-pill ${Meta.className}`}><Icon size={12} strokeWidth={2.4} aria-hidden="true" />{status}</span>;
}
function ProgressBar({ value, small = false }) {
  return <div className={`progress-track ${small ? "progress-small" : ""}`} role="progressbar" aria-label="Task progress" aria-valuemin="0" aria-valuemax="100" aria-valuenow={value}><span style={{ width: `${value}%` }} /></div>;
}
function PageTitle({ eyebrow, title, description, action }) {
  return <div className="page-title-row"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{description}</p></div>{action}</div>;
}
function LoginScreen({ onDemoAccess }) {
  return <main className="login-screen">
    <section className="login-panel" aria-labelledby="login-title">
      <div className="login-brand"><span className="brand-mark"><Command size={19} strokeWidth={2.5} /></span><strong>delegator<span>ai</span></strong></div>
      <div className="login-copy">
        <span className="eyebrow">TEAM LEAD WORKSPACE</span>
        <h1 id="login-title">Keep the work moving.</h1>
        <p>DelegatorAI gives team leads one place to review projects, blockers, and follow-up decisions.</p>
      </div>
      <div className="login-actions">
        <button className="button button-primary login-google-button" disabled title="Google authentication is not configured for this frontend">
          <span className="google-glyph" aria-hidden="true">G</span> Continue with Google
        </button>
        <p className="login-unavailable" role="status">Google Sign-In is unavailable because this project has no configured authentication endpoint or OAuth client.</p>
        <button className="button button-secondary login-demo-button" onClick={onDemoAccess}>Open demo workspace</button>
        <p className="login-demo-note">Demo access uses local sample data. It is not an authenticated team-lead session.</p>
      </div>
      <div className="login-boundary"><ShieldCheck size={15} aria-hidden="true"/><span>Live access will require backend-verified identity and team-lead authorization.</span></div>
    </section>
  </main>;
}

const initialTheme = (() => {
  try {
    return localStorage.getItem("delegatorai-theme") || "dark";
  } catch {
    return "dark";
  }
})();
if (typeof document !== "undefined") document.documentElement.dataset.theme = initialTheme;

export default function App() {
  const [page, setPage] = useState("Overview");
  const [tasks, setTasks] = useState(initialTasks);
  const [people, setPeople] = useState(initialPeople);
  const [activity, setActivity] = useState(initialActivity);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All statuses");
  const [selectedTask, setSelectedTask] = useState(null);
  const [showCreate, setShowCreate] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfile, setShowProfile] = useState(false);
  const [mobileNav, setMobileNav] = useState(false);
  const [aiEnabled, setAiEnabled] = useState(true);
  const [toast, setToast] = useState("");
  const [apiState, setApiState] = useState("demo");
  const [accessMode, setAccessMode] = useState(null);
  const [theme, setTheme] = useState(initialTheme);
  const [newTask, setNewTask] = useState({ title: "", description: "", assignee: "", priority: "Medium", dueDate: "2026-10-22" });

  const completed = tasks.filter(t => t.status === "Completed").length;
  const blocked = tasks.filter(t => t.status === "Blocked").length;
  const inProgress = tasks.filter(t => t.status === "In Progress").length;
  const completion = tasks.length ? Math.round(completed / tasks.length * 100) : 0;

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("delegatorai-theme", theme);
    } catch {
      setToast("Theme preference could not be saved.");
    }
  }, [theme]);

  useEffect(() => {
    let alive = true;
    Promise.all([api.getTasks(), api.getParticipants()]).then(async ([taskData, participantData]) => {
      if (!alive) return;
      if (!Array.isArray(taskData) || !Array.isArray(participantData)) {
        throw new Error("Backend returned an invalid task or participant list.");
      }
      const histories = await Promise.all(
        taskData.map(task => api.getTaskHistory(task.id))
      );
      if (histories.some(history => !Array.isArray(history))) {
        throw new Error("Backend returned an invalid task history.");
      }
      const nextPeople = participantData.map(normalizeParticipant);
      setTasks(taskData.map(normalizeTask));
      setPeople(nextPeople);
      setActivity(histories.flat().sort((a, b) => Date.parse(b.time) - Date.parse(a.time)));
      setNewTask(current => ({ ...current, assignee: nextPeople[0]?.id || "" }));
      setApiState("connected");
    }).catch(() => { if (alive) setApiState("offline"); });
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => setToast(""), 3000);
    return () => clearTimeout(timer);
  }, [toast]);

  useEffect(() => {
    function handleKeyDown(event) {
      if (event.key !== "Escape") return;
      if (mobileNav) setMobileNav(false);
      if (showNotifications) setShowNotifications(false);
      if (showProfile) setShowProfile(false);
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [mobileNav, showNotifications, showProfile]);

  function addActivity(title, detail, kind = "update") {
    setActivity(prev => [{ id: Date.now(), title, detail, time: "Just now", kind }, ...prev]);
  }
  async function updateTask(id, patch) {
    const current = tasks.find(t => t.id === id);
    if (!current) return;
    try {
      const updated = apiState === "connected"
        ? normalizeTask(await api.updateTask(id, patch))
        : { ...current, ...patch };
      setTasks(prev => prev.map(t => t.id === id ? updated : t));
      addActivity("Task updated", `“${current.title}” was updated.`, patch.status === "Completed" ? "success" : "update");
      setSelectedTask(updated);
      setToast(apiState === "connected" ? "Task saved to backend" : "Task updated in demo");
    } catch (error) {
      setToast(`Could not save task: ${error.message}`);
    }
  }
  async function createTask(e) {
    e.preventDefault();
    if (!newTask.title.trim()) return;
    const person = people.find(p => p.id === newTask.assignee) || (apiState === "connected" ? null : initialPeople[2]);
    if (!person) {
      setToast("Add participants to the backend before assigning a task.");
      return;
    }
    try {
      const created = apiState === "connected"
        ? normalizeTask(await api.createTask({
          title: newTask.title.trim(),
          project_id: "college-app",
          owner_id: person.id,
          deadline: newTask.dueDate,
          description: newTask.description.trim(),
          priority: newTask.priority,
        }))
        : normalizeTask({
          id: `T-${Math.floor(100 + Math.random() * 900)}`,
          title: newTask.title.trim(),
          description: newTask.description.trim() || "No description added yet.",
          assignee: person.name,
          owner_id: person.id,
          status: "Pending",
          priority: newTask.priority,
          dueDate: new Date(`${newTask.dueDate}T12:00:00`).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
          progress: 0,
          project: "CampusConnect",
          updated: "Just now",
          blocker: "",
        });
      setTasks(prev => [created, ...prev]);
      addActivity("New task created", `“${created.title}” assigned to ${person.name}.`, "success");
      setShowCreate(false);
      setNewTask({ title: "", description: "", assignee: people[0]?.id || "", priority: "Medium", dueDate: "2026-10-22" });
      setToast(apiState === "connected" ? "Task created in backend" : "Task created in demo");
    } catch (error) {
      setToast(`Could not create task: ${error.message}`);
    }
  }

  const filteredTasks = useMemo(() => tasks.filter(t => {
    const matchesSearch = `${t.title} ${t.assignee} ${t.id}`.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "All statuses" || t.status === statusFilter;
    return matchesSearch && matchesStatus;
  }), [tasks, search, statusFilter]);

  const pageDescriptions = {
    "Overview": ["YOUR WORKSPACE", "Good afternoon, Aditi 👋", "Here’s what’s happening with CampusConnect today."],
    "Projects": ["PROJECT SPACE", "Your projects", "Keep the whole team moving in one place."],
    "My Tasks": ["PERSONAL WORKSPACE", "My tasks", "A clear view of what needs your attention next."],
    "Team Members": ["YOUR PEOPLE", "Team members", "See ownership, workload and how your team is doing."],
    "AI Coordinator": ["AGENT CONTROL CENTER", "AI Coordinator", "A little follow-up goes a long way. Stay in control of every nudge."],
    "Activity Log": ["AUDIT TRAIL", "Activity log", "A transparent timeline of task updates and coordinator actions."],
    "Settings": ["WORKSPACE CONFIGURATION", "Settings", "Manage your workspace preferences and coordinator behavior."],
  };
  const info = pageDescriptions[page] || pageDescriptions.Overview;

  if (!accessMode) return <LoginScreen onDemoAccess={() => setAccessMode("demo")} />;

  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? "sidebar-open" : ""}`}>
      <div className="brand-row">
        <div className="brand-mark"><Command size={19} strokeWidth={2.5} /></div>
        <div className="brand-name">delegator<span>ai</span><small>PROJECT WORKSPACE</small></div>
        <button className="icon-btn sidebar-close" onClick={() => setMobileNav(false)} aria-label="Close menu"><X size={18} /></button>
      </div>
      <button className="workspace-switcher" onClick={() => setToast("CampusConnect is your active workspace.")}>
        <span className="workspace-icon">C</span><span className="workspace-name"><strong>CampusConnect</strong><small>Free workspace</small></span><ChevronDown size={15} />
      </button>
      <div className="nav-scroll">
        {navGroups.map(group => <div className="nav-group" key={group.label}>
          <div className="nav-label">{group.label === "WORKSPACE" ? "Workspace" : "Intelligence"}</div>
          {group.items.map(item => {
            const Icon = item.icon;
            return <button key={item.id} className={`nav-item ${page === item.id ? "active" : ""}`} aria-current={page === item.id ? "page" : undefined} onClick={() => { setPage(item.id); setMobileNav(false); }}>
              <Icon size={17} aria-hidden="true" /><span>{item.id}</span>{item.badge && <span className="nav-live">{item.badge}</span>}
            </button>;
          })}
        </div>)}
      </div>
      <div className="sidebar-bottom">
        <div className="ai-mini-card">
          <div className="ai-mini-top"><span className={`online-dot ${aiEnabled ? "" : "offline"}`} /><span>{aiEnabled ? "AI coordinator active" : "AI coordinator paused"}</span><Sparkles size={14} /></div>
          <p>{aiEnabled ? "Demo queue includes pending follow-ups." : "Automatic follow-ups are paused."}</p>
          <button onClick={() => { setPage("AI Coordinator"); setMobileNav(false); }}>Manage agent <ArrowRight size={13} /></button>
        </div>
        <button className={`nav-item ${page === "Settings" ? "active" : ""}`} aria-current={page === "Settings" ? "page" : undefined} onClick={() => { setPage("Settings"); setMobileNav(false); }}><Settings size={17} aria-hidden="true" /><span>Settings</span></button>
        <button className="user-card" onClick={() => setShowProfile(v => !v)} aria-label="Open Aditi Sharma profile menu" aria-expanded={showProfile}>
          <Avatar initials="AS" color="purple" /><span className="user-copy"><strong>Aditi Sharma</strong><small>Project Lead</small></span><MoreHorizontal size={18} aria-hidden="true" />
        </button>
      </div>
    </aside>
    {mobileNav && <button className="mobile-overlay" aria-label="Close navigation" onClick={() => setMobileNav(false)} />}
    <main className="main-area">
      <header className="topbar">
        <div className="breadcrumbs"><button className="mobile-menu icon-btn" onClick={() => setMobileNav(true)} aria-label="Open navigation menu" aria-expanded={mobileNav}><Menu size={20} aria-hidden="true" /></button><span>Workspace</span><ChevronRight size={14} aria-hidden="true" /><strong>{page}</strong></div>
        <div className="topbar-actions">
          <div className="connection-indicator"><span className={`online-dot ${apiState !== "connected" ? "offline" : ""}`} />{apiState === "connected" ? "Backend connected" : apiState === "offline" ? "Backend unavailable · demo data" : "Demo mode"}</div>
          <button className="icon-btn search-toggle" onClick={() => document.getElementById("global-search")?.focus()} aria-label="Search"><Search size={18} aria-hidden="true" /></button>
          <button className="icon-btn notification-btn" onClick={() => setShowNotifications(v => !v)} aria-label="Notifications" aria-expanded={showNotifications}><Bell size={18} aria-hidden="true" /><i aria-hidden="true" /></button>
          <button className="topbar-avatar" onClick={() => setShowProfile(v => !v)} aria-label="Open Aditi Sharma profile menu" aria-expanded={showProfile}><Avatar initials="AS" color="purple" size="small" /></button>
        </div>
        {showNotifications && <div className="floating-menu notifications-menu"><div className="floating-head"><strong>Notifications</strong><span className="soft-tag">3 new</span></div><div className="notification-row"><span className="notification-icon purple-bg"><Bot size={15}/></span><div><strong>AI follow-up ready</strong><p>Neha's task needs a check-in.</p><small>12 min ago</small></div></div><div className="notification-row"><span className="notification-icon green-bg"><Check size={15}/></span><div><strong>Task completed</strong><p>Onboarding wireframes are done.</p><small>1 hour ago</small></div></div><button className="text-button" onClick={() => { setPage("Activity Log"); setShowNotifications(false); }}>View activity log <ArrowRight size={14}/></button></div>}
        {showProfile && <div className="floating-menu profile-menu"><div className="profile-menu-person"><Avatar initials="AS" color="purple"/><div><strong>Aditi Sharma</strong><small>Demo workspace · not signed in</small></div></div><button onClick={() => {setPage("Settings");setShowProfile(false)}}><Settings size={15}/> Workspace settings</button><button onClick={() => {setShowProfile(false);setToast("You are using the local demo workspace.")}}><ExternalLink size={15}/> Demo workspace</button><button onClick={() => {setShowProfile(false);setAccessMode(null)}}><PanelLeftClose size={15}/> Leave demo workspace</button></div>}
      </header>
      <div className="page-content">
        <PageTitle eyebrow={info[0]} title={info[1].replace(" 👋", "")} description={info[2]} action={
          <div className="title-actions">{page !== "Settings" && <button className="button button-secondary" onClick={() => setToast("Workspace data is up to date.")}><RefreshCw size={15}/> Refresh</button>}{["Overview","Projects","My Tasks"].includes(page) && <button className="button button-primary" onClick={() => setShowCreate(true)}><Plus size={16}/> New task</button>}</div>
        } />

        {page === "Overview" && <Overview tasks={tasks} people={people} activity={activity} completed={completed} blocked={blocked} inProgress={inProgress} completion={completion} setPage={setPage} setSelectedTask={setSelectedTask} setShowCreate={setShowCreate} aiEnabled={aiEnabled} />}
        {page === "Projects" && <Projects tasks={tasks} people={people} setPage={setPage} setSelectedTask={setSelectedTask} setShowCreate={setShowCreate} />}
        {page === "My Tasks" && <TaskWorkspace tasks={filteredTasks} setSelectedTask={setSelectedTask} search={search} setSearch={setSearch} statusFilter={statusFilter} setStatusFilter={setStatusFilter} />}
        {page === "Team Members" && <TeamMembers tasks={tasks} people={people} />}
        {page === "AI Coordinator" && <Coordinator tasks={tasks} activity={activity} apiState={apiState} enabled={aiEnabled} setEnabled={setAiEnabled} setToast={setToast} addActivity={addActivity} />}
        {page === "Activity Log" && <ActivityLog activity={activity} />}
        {page === "Settings" && <SettingsPage aiEnabled={aiEnabled} setAiEnabled={setAiEnabled} setToast={setToast} theme={theme} setTheme={setTheme} />}
      </div>
      <footer className="footer"><span>© 2026 DelegatorAI</span><span><span className="footer-dot" /> All systems operational <span className="footer-separator">·</span> Built for teams that ship</span></footer>
    </main>
    {selectedTask && <TaskDrawer task={selectedTask} onClose={() => setSelectedTask(null)} onUpdate={updateTask} />}
    {showCreate && <div className="modal-backdrop" onMouseDown={e => { if (e.target === e.currentTarget) setShowCreate(false); }}><form className="modal create-modal" onSubmit={createTask}>
      <div className="modal-heading"><div><div className="eyebrow">CAMPUSCONNECT</div><h2>Create a task</h2><p>Give your teammate a clear next step.</p></div><button type="button" className="icon-btn" onClick={() => setShowCreate(false)}><X size={19}/></button></div>
      <label className="field-label">Task title <span>*</span><input required autoFocus placeholder="e.g. Implement password reset flow" value={newTask.title} onChange={e => setNewTask({...newTask,title:e.target.value})}/></label>
      <label className="field-label">Description<textarea rows="3" placeholder="What needs to be done? Include acceptance criteria..." value={newTask.description} onChange={e => setNewTask({...newTask,description:e.target.value})}/></label>
      <div className="form-grid">      <label className="field-label">Assignee<select required value={newTask.assignee} onChange={e => setNewTask({...newTask,assignee:e.target.value})}>{people.map(p=><option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label className="field-label">Priority<select value={newTask.priority} onChange={e => setNewTask({...newTask,priority:e.target.value})}><option>Low</option><option>Medium</option><option>High</option></select></label></div>
      <label className="field-label">Due date<input type="date" value={newTask.dueDate} onChange={e => setNewTask({...newTask,dueDate:e.target.value})}/></label>
      <div className="chat-preview"><div className="chat-preview-icon"><MessageCircle size={16}/></div><div><strong>Google Chat notification preview</strong><p>Hey {newTask.assignee.split(" ")[0] || "teammate"} — you’ve been assigned a new task: “{newTask.title || "Your new task"}”.</p><small>Preview only · Real messaging requires backend integration</small></div></div>
      <div className="modal-footer"><button type="button" className="button button-secondary" onClick={() => setShowCreate(false)}>Cancel</button><button type="submit" className="button button-primary"><Plus size={15}/> Create task</button></div>
    </form></div>}
    {toast && <div className="toast"><span className="toast-check"><Check size={14}/></span>{toast}<button onClick={() => setToast("")}><X size={14}/></button></div>}
  </div>;
}

function normalizeTask(t) {
  const statusMap = { PENDING: "Pending", IN_PROGRESS: "In Progress", BLOCKED: "Blocked", COMPLETE: "Completed", COMPLETED: "Completed", Complete: "Completed" };
  return { ...t, id: String(t.id ?? `T-${Date.now()}`), title: t.title || "Untitled task", description: t.description || "", assignee: t.assignee || t.owner || "Unassigned", initials: t.initials || (t.assignee || t.owner || "U").split(" ").map(x => x[0]).join("").slice(0,2).toUpperCase(), role: t.role || "Team member", status: statusMap[t.status] || t.status || "Pending", priority: t.priority || "Medium", dueDate: t.dueDate || t.due_date || "Not set", progress: t.progress ?? 0, project: t.project || "CampusConnect", updated: t.updated || "Recently", blocker: t.blocker || "" };
}

function normalizeParticipant(person) {
  const initials = (person.name || "U").split(" ").map(part => part[0]).join("").slice(0, 2).toUpperCase();
  return { ...person, initials, role: "Team member", color: avatarColor(initials) };
}

function Overview({ tasks, people, activity, completed, blocked, inProgress, completion, setPage, setSelectedTask, setShowCreate, aiEnabled }) {
  const pending = tasks.filter(t => t.status === "Pending").length;
  const assignedMembers = new Set(tasks.map(task => task.assignee).filter(Boolean)).size;
  const attentionTasks = [...tasks]
    .filter(task => task.status !== "Completed")
    .sort((a, b) => attentionScore(b) - attentionScore(a))
    .slice(0, 4);
  const upcomingTasks = [...tasks]
    .filter(task => task.status !== "Completed")
    .sort((a, b) => dueDateScore(a) - dueDateScore(b))
    .slice(0, 3);
  const workload = people.map(person => {
    const owned = tasks.filter(task => task.assignee === person.name);
    const done = owned.filter(task => task.status === "Completed").length;
    return { ...person, count: owned.length, completion: owned.length ? Math.round(done / owned.length * 100) : 0 };
  }).filter(person => person.count > 0).sort((a, b) => b.count - a.count);
  const hasAttention = attentionTasks.length > 0;
  return <>
    <section className="overview-hero">
      <div className="overview-hero-copy">
        <span className="overview-kicker"><span className="project-chip-dot"/> Active project</span>
        <h2>CampusConnect</h2>
        <p>Student collaboration, without the chaos.</p>
        <div className="overview-meta">
          <span><Users size={14} aria-hidden="true"/> {assignedMembers} assigned members</span>
          <span><ShieldCheck size={14} aria-hidden="true"/> {blocked ? `${blocked} blocker${blocked === 1 ? "" : "s"} need attention` : "No active blockers"}</span>
        </div>
      </div>
      <div className="overview-progress-card">
        <div className="overview-progress-heading"><span>Project completion</span><strong>{completion}%</strong></div>
        <ProgressBar value={completion}/>
        <div className="overview-progress-foot"><span>{completed} of {tasks.length} tasks complete</span><span>{tasks.length - completed} open</span></div>
      </div>
    </section>
    <div className="stats-grid">
      <StatCard label="Total tasks" value={tasks.length} caption="Across this project" icon={ListTodo} tone="blue" trend="All work items"/>
      <StatCard label="In progress" value={inProgress} caption="Being worked on now" icon={CircleDot} tone="purple" trend="Active"/>
      <StatCard label="Blocked tasks" value={blocked} caption="Need attention" icon={AlertCircle} tone="orange" trend={blocked ? "Needs action" : "All clear"}/>
      <StatCard label="Completed" value={completed} caption="Tasks shipped" icon={CheckCheck} tone="green" trend={`${completion}% complete`}/>
    </div>
    <div className="overview-grid">
      <section className="panel overview-attention-panel"><div className="panel-heading"><div><h3>Needs attention</h3><p>Prioritized work that may need a decision</p></div><button className="text-button" onClick={() => setPage("Projects")}>View all tasks <ArrowRight size={14}/></button></div>
        {hasAttention ? <div className="overview-task-list">{attentionTasks.map(task => <OverviewTaskRow key={task.id} task={task} onSelect={setSelectedTask}/>)}</div> : <EmptyOverviewState icon={CheckCheck} title="Everything is moving" detail="No open tasks need attention right now."/>}
      </section>
      <section className="panel overview-insights-panel"><div className="panel-heading"><div><h3>Project health</h3><p>Work distribution and team load</p></div></div>
        <div className="overview-distribution">
          <div className="donut-wrap"><div className="donut" style={{background:`conic-gradient(var(--color-complete) 0 ${tasks.length ? completed / tasks.length * 100 : 0}%, var(--color-progress) ${tasks.length ? completed / tasks.length * 100 : 0}% ${tasks.length ? (completed + inProgress) / tasks.length * 100 : 0}%, var(--color-blocked) ${tasks.length ? (completed + inProgress) / tasks.length * 100 : 0}% ${tasks.length ? (completed + inProgress + blocked) / tasks.length * 100 : 0}%, var(--color-pending) ${tasks.length ? (completed + inProgress + blocked) / tasks.length * 100 : 0}% 100%)`}}><div className="donut-center"><strong>{tasks.length}</strong><span>Total tasks</span></div></div></div>
          <div className="legend-list">{[["Completed",completed,"--color-complete"],["In Progress",inProgress,"--color-progress"],["Blocked",blocked,"--color-blocked"],["Pending",pending,"--color-pending"]].map(([label,value,color])=><div className="legend-row" key={label}><span className="legend-label"><i style={{background:`var(${color})`}}/>{label}</span><strong>{value}<small>{tasks.length ? Math.round(value / tasks.length * 100) : 0}%</small></strong></div>)}</div>
        </div>
        <div className="workload-heading"><h4>Team workload</h4><span>{assignedMembers} assigned</span></div>
        <div className="workload-list">{workload.length ? workload.slice(0, 3).map(person => <div className="workload-row" key={person.name}><Avatar initials={person.initials} color={person.color} size="small"/><div className="workload-person"><strong>{person.name}</strong><small>{person.count} task{person.count === 1 ? "" : "s"} · {person.completion}% complete</small></div><ProgressBar value={person.completion} small/></div>) : <p className="overview-muted">No assigned work yet.</p>}</div>
      </section>
    </div>
    <div className="lower-grid">
      <section className="panel deadlines-panel"><div className="panel-heading"><div><h3>Upcoming deadlines</h3><p>Open work ordered by due date</p></div><button className="text-button" onClick={()=>setPage("Projects")}>See all <ArrowRight size={14}/></button></div>
        {upcomingTasks.length ? upcomingTasks.map(task => <OverviewDeadlineRow key={task.id} task={task} onSelect={setSelectedTask}/>) : <EmptyOverviewState icon={CalendarDays} title="No upcoming deadlines" detail="Open tasks will appear here when they have due dates."/>}
      </section>
      <section className="panel activity-panel"><div className="panel-heading"><div><h3>Recent activity</h3><p>Latest updates from your team</p></div><button className="text-button" onClick={()=>setPage("Activity Log")}>View log <ArrowRight size={14}/></button></div>
        {activity.length ? <div className="activity-list">{activity.slice(0,4).map(a=><ActivityItem key={a.id} item={a}/>)}</div> : <EmptyOverviewState icon={Activity} title="No activity yet" detail="Updates will appear here as the team works."/>}
      </section>
    </div>
    <div className="bottom-nudge"><div className="nudge-icon"><Sparkles size={18}/></div><div className="nudge-copy"><strong>{aiEnabled ? "Your AI coordinator is keeping things moving" : "Your AI coordinator is paused"}</strong><p>{aiEnabled ? "It reviews open task statuses and flags blockers before they become surprises." : "Resume the agent when you're ready to prepare follow-ups again."}</p></div><button className="button button-secondary" onClick={()=>setPage("AI Coordinator")}>Open coordinator <ArrowRight size={14}/></button></div>
  </>;
}

function StatCard({label,value,caption,icon:Icon,tone,trend}) {
  return <div className="stat-card"><div className="stat-top"><span>{label}</span><span className={`stat-icon ${tone}`}><Icon size={17}/></span></div><div className="stat-value">{value}</div><div className="stat-bottom"><span>{caption}</span><span className={`stat-trend ${tone}`}>{trend}</span></div></div>;
}
function OverviewTaskRow({ task, onSelect }) {
  const overdue = isTaskOverdue(task);
  return <button className={`overview-task-row ${task.status === "Blocked" ? "is-blocked" : ""}`} onClick={() => onSelect(task)}>
    <span className={`overview-task-indicator priority-${task.priority.toLowerCase()}`} aria-hidden="true"/>
    <span className="overview-task-content"><strong>{task.title}</strong><small>{task.assignee} · {task.id}</small></span>
    <span className="overview-task-state"><StatusPill status={task.status}/><small className={overdue ? "is-overdue" : ""}>{overdue ? "Overdue" : task.dueDate}</small></span>
    <ChevronRight size={16} aria-hidden="true"/>
  </button>;
}
function OverviewDeadlineRow({ task, onSelect }) {
  const overdue = isTaskOverdue(task);
  const [month, day] = task.dueDate.split(" ");
  return <button className={`deadline-row ${overdue ? "is-overdue" : ""}`} onClick={() => onSelect(task)}>
    <span className={`deadline-date ${overdue ? "date-overdue" : ""}`}><strong>{day || "—"}</strong><small>{month || ""}</small></span>
    <span className="deadline-main"><strong>{task.title}</strong><small>{task.assignee} · {task.id}</small><ProgressBar value={task.progress} small/></span>
    <span className="deadline-right"><StatusPill status={task.status}/><ChevronRight size={15} aria-hidden="true"/></span>
  </button>;
}
function EmptyOverviewState({ icon: Icon, title, detail }) {
  return <div className="overview-empty"><Icon size={20} aria-hidden="true"/><strong>{title}</strong><p>{detail}</p></div>;
}
function dueDateScore(task) {
  const date = parseTaskDate(task.dueDate);
  return date ? date.getTime() : Number.MAX_SAFE_INTEGER;
}
function isTaskOverdue(task) {
  const date = parseTaskDate(task.dueDate);
  if (!date || task.status === "Completed") return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  return date < today;
}
function parseTaskDate(value) {
  if (!value || value === "Not set") return null;
  const date = new Date(value.includes(",") ? value : `${value}, ${new Date().getFullYear()}`);
  return Number.isNaN(date.getTime()) ? null : date;
}
function attentionScore(task) {
  return (task.status === "Blocked" ? 4 : 0) + (isTaskOverdue(task) ? 2 : 0) + (task.status === "In Progress" ? 1 : 0);
}
function ActivityItem({item}) {
  const Icon = item.kind==="success" ? Check : item.kind==="warning" ? AlertCircle : item.kind==="bot" ? Bot : Activity;
  return <div className="activity-item"><span className={`activity-icon ${item.kind}`}><Icon size={14}/></span><div className="activity-detail"><strong>{item.title}</strong><p>{item.detail}</p><small>{item.time}</small></div></div>;
}
function Projects({tasks,people,setPage,setSelectedTask,setShowCreate}) {
  const [tab,setTab]=useState("Board");
  const columns=["Pending","In Progress","Blocked","Completed"];
  const completed = tasks.filter(task => task.status === "Completed").length;
  const completion = tasks.length ? Math.round(completed / tasks.length * 100) : 0;
  return <><section className="project-management-boundary panel" aria-labelledby="project-management-title"><div><span className="eyebrow">PROJECT ACCESS</span><h2 id="project-management-title">CampusConnect</h2><p>This demo contains one local project. Multi-project lists, verified project IDs, and project switching require backend project endpoints.</p></div><div className="project-boundary-actions"><button className="button button-secondary button-sm" disabled title="Project creation requires a backend endpoint"><Plus size={14} aria-hidden="true"/> Create project unavailable</button><button className="button button-secondary button-sm" disabled title="Project membership requires a backend endpoint"><Users size={14} aria-hidden="true"/> Manage members unavailable</button></div><span className="integration-status demo"><i/> Demo project</span></section><section className="project-detail-card"><div className="project-detail-icon" aria-hidden="true">C</div><div className="project-detail-main"><div className="project-title-line"><h2>CampusConnect</h2><span className="status-pill completed"><CircleCheck size={12} aria-hidden="true"/> Active</span></div><p>A student collaboration platform that makes group work easier to organize, track and finish.</p><div className="project-detail-meta"><span><Users size={14} aria-hidden="true"/> {people.length} members</span><span><ListTodo size={14} aria-hidden="true"/> {tasks.length} tasks</span></div><div className="project-progress-summary"><div><span>Project progress</span><strong>{completion}%</strong></div><ProgressBar value={completion}/><small>{completed} of {tasks.length} tasks complete</small></div></div><button className="button button-primary" onClick={()=>setShowCreate(true)}><Plus size={15} aria-hidden="true"/> Add task</button></section>
    <div className="board-toolbar"><div><div className="board-toolbar-title"><h3>Project work</h3><span>{tasks.length} task{tasks.length === 1 ? "" : "s"}</span></div><div className="tab-switcher" role="tablist" aria-label="Project view"><button role="tab" aria-selected={tab==="Board"} className={tab==="Board"?"selected":""} onClick={()=>setTab("Board")}><LayoutDashboard size={14} aria-hidden="true"/> Board</button><button role="tab" aria-selected={tab==="List"} className={tab==="List"?"selected":""} onClick={()=>setTab("List")}><ListTodo size={14} aria-hidden="true"/> List</button></div></div><div className="toolbar-right"><span className="member-stack" aria-label={`${people.length - 1} additional team members`}>{people.slice(1,5).map(p=><Avatar key={p.name} initials={p.initials} color={p.color} size="tiny"/>)}</span><button className="button button-secondary button-sm" onClick={()=>setPage("Team Members")}><Users size={14} aria-hidden="true"/> Team</button></div></div>
    {tab==="Board"?<div className="kanban-grid">{columns.map(status=>{const group=tasks.filter(t=>t.status===status);return <div className="kanban-column" key={status}><div className="kanban-heading"><span className={`column-dot ${statusMeta[status].className}`}/><strong>{status}</strong><span className="column-count">{group.length}</span><button className="row-more" aria-label={`Add task to ${status}`} onClick={()=>setShowCreate(true)}><Plus size={15} aria-hidden="true"/></button></div>{group.map(t=><button className="kanban-card" key={t.id} onClick={()=>setSelectedTask(t)}><div className="kanban-card-top"><span className={`priority-label priority-text-${t.priority.toLowerCase()}`}>{t.priority} priority</span><MoreHorizontal size={15} aria-hidden="true"/></div><strong>{t.title}</strong><p>{t.description}</p>{t.status!=="Pending"&&<ProgressBar value={t.progress} small/>}{t.blocker&&<div className="blocker-note"><AlertCircle size={13}/>{t.blocker}</div>}<div className="kanban-card-bottom"><span className="task-id">{t.id}</span><span className="kanban-due"><CalendarDays size={12}/>{t.dueDate}</span><Avatar initials={t.initials} color={avatarColor(t.initials)} size="tiny"/></div></button>)}{group.length===0&&<div className="empty-column">No tasks here yet</div>}</div>})}</div>:<div className="panel"><TaskTable tasks={tasks} setSelectedTask={setSelectedTask}/></div>}
  </>;
}
function TaskWorkspace({tasks,setSelectedTask,search,setSearch,statusFilter,setStatusFilter}) {
  return <><div className="task-workspace-intro"><div><h2>Find the next task to move</h2><p>Search by task or teammate, then filter by status.</p></div><span className="task-result-count">{tasks.length} result{tasks.length === 1 ? "" : "s"}</span></div><div className="filter-bar"><div className="search-field"><Search size={16} aria-hidden="true"/><input id="global-search" aria-label="Search tasks or teammates" placeholder="Search tasks or teammates..." value={search} onChange={e=>setSearch(e.target.value)}/><kbd>⌘ K</kbd></div><label className="sr-only" htmlFor="task-status-filter">Filter tasks by status</label><select id="task-status-filter" aria-label="Filter tasks by status" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}><option>All statuses</option>{Object.keys(statusMeta).map(s=><option key={s}>{s}</option>)}</select><button className="button button-secondary button-sm" onClick={()=>{setSearch("");setStatusFilter("All statuses")}}><Filter size={14} aria-hidden="true"/> Reset filters</button></div><div className="panel task-results-panel"><TaskTable tasks={tasks} setSelectedTask={setSelectedTask}/></div></>;
}
function TaskTable({tasks,setSelectedTask}) {
  return <div className="task-table-wrap"><table className="task-table full-table"><thead><tr><th>TASK</th><th>ASSIGNEE</th><th>STATUS</th><th>PRIORITY</th><th>DUE DATE</th><th/></tr></thead><tbody>{tasks.map(t=><tr key={t.id} onClick={()=>setSelectedTask(t)}><td><div className="task-name-cell"><span className={`task-priority priority-${t.priority.toLowerCase()}`}/><div><strong>{t.title}</strong><small>{t.id} · {t.role}</small></div></div></td><td><div className="assignee-cell"><Avatar initials={t.initials} color={avatarColor(t.initials)} size="small"/><span>{t.assignee}</span></div></td><td><StatusPill status={t.status}/></td><td><span className={`priority-label priority-text-${t.priority.toLowerCase()}`}>{t.priority}</span></td><td><span className="due-date"><CalendarDays size={12}/>{t.dueDate}</span></td><td><button className="row-more" aria-label={`Open actions for ${t.title}`}><MoreHorizontal size={17} aria-hidden="true"/></button></td></tr>)}</tbody></table>{tasks.length===0&&<div className="empty-state" role="status"><Search size={23} aria-hidden="true"/><strong>No tasks match your filters</strong><p>Try another search or clear your filters.</p></div>}</div>;
}
function TeamMembers({tasks,people}) {
  const assignedTasks = tasks.filter(task => task.assignee && people.some(person => person.name === task.assignee));
  const unassignedTasks = tasks.filter(task => !task.assignee || !people.some(person => person.name === task.assignee)).length;
  const completedTasks = tasks.filter(task => task.status === "Completed").length;
  return <><div className="team-summary-grid"><div className="panel team-summary"><span className="stat-icon purple"><Users size={17} aria-hidden="true"/></span><div><strong>{people.length}</strong><span>Team members</span></div></div><div className="panel team-summary"><span className="stat-icon blue"><ListTodo size={17} aria-hidden="true"/></span><div><strong>{assignedTasks.length}</strong><span>Assigned tasks</span></div></div><div className="panel team-summary"><span className="stat-icon green"><CheckCheck size={17} aria-hidden="true"/></span><div><strong>{completedTasks}</strong><span>Tasks completed</span></div></div></div>
    <section className="panel team-panel"><div className="panel-heading"><div><h3>Team roster</h3><p>Workload derived from the current task list</p></div><button className="button button-secondary button-sm" onClick={()=>alert("Invitations will be available after backend integration.")}><Plus size={14} aria-hidden="true"/> Invite member</button></div>{people.length ? <div className="team-roster">{people.map(p=>{const owned=tasks.filter(t=>t.assignee===p.name);const done=owned.filter(t=>t.status==="Completed").length;const blocked=owned.filter(t=>t.status==="Blocked").length;return <article className={`team-member-card ${blocked ? "has-blocker" : ""}`} key={p.name}><div className="team-member-main"><Avatar initials={p.initials} color={p.color}/><div><strong>{p.name}</strong><small>{p.role}</small><a href={`mailto:${p.email}`}>{p.email}</a></div></div><div className="team-member-work"><div><span>Assigned</span><strong>{owned.length}</strong></div><div><span>Complete</span><strong>{owned.length ? Math.round(done / owned.length * 100) : 0}%</strong></div>{blocked ? <StatusPill status="Blocked"/> : <span className="member-status"><i/> Active</span>}</div><div className="team-member-progress"><ProgressBar value={owned.length ? done / owned.length * 100 : 0} small/><span>{blocked ? `${blocked} blocked` : owned.length ? `${owned.length} task${owned.length === 1 ? "" : "s"} in progress` : "No tasks assigned"}</span></div></article>})}</div> : <EmptyOverviewState icon={Users} title="No team members yet" detail="Members will appear here when they are added to the workspace."/>}{unassignedTasks > 0 && <div className="team-unassigned"><AlertCircle size={15} aria-hidden="true"/><span>{unassignedTasks} task{unassignedTasks === 1 ? "" : "s"} without a matched assignee</span></div>}</section>
    <div className="invite-banner"><div className="invite-illustration"><Users size={21} aria-hidden="true"/><Plus size={12} aria-hidden="true"/></div><div><strong>Great work is a team sport.</strong><p>Bring everyone into the same workspace to keep work visible and blockers small.</p></div><button className="button button-secondary" onClick={()=>alert("Invitations will be enabled once the backend is connected.")}>Invite teammates <ArrowRight size={14} aria-hidden="true"/></button></div>
  </>;
}
function Coordinator({tasks,activity,apiState,enabled,setEnabled,setToast,addActivity}) {
  const [tab,setTab]=useState("Follow-up queue");
  const [cadence,setCadence]=useState("Every 24 hours");
  const [quietHours,setQuietHours]=useState(true);
  const [autoStatus,setAutoStatus]=useState(true);
  const [messages,setMessages]=useState({});
  const pending=tasks.filter(t=>t.status!=="Completed");
  async function sendFollowup(task) {
    if (apiState === "connected") {
      setMessages(prev=>({...prev,[task.id]:"sending"}));
      try {
        const result = await api.followUpTask(task.id);
        if (result.status !== "sent") throw new Error("Backend did not confirm that the message was sent.");
        setMessages(prev=>({...prev,[task.id]:"sent"}));
        addActivity("Follow-up sent",`A Google Chat follow-up was sent for “${task.title}”.`,"bot");
        setToast("Follow-up sent in Google Chat");
      } catch (error) {
        setMessages(prev=>{const next={...prev};delete next[task.id];return next;});
        setToast(`Google Chat follow-up failed: ${error.message}`);
      }
      return;
    }
    setMessages(prev=>({...prev,[task.id]:"demo"}));
    addActivity("Follow-up queued",`A follow-up for “${task.title}” was queued in demo mode.`,"bot");
    setToast("Follow-up queued in demo mode");
  }
  const recentActivity=activity.filter(a=>a.kind==="bot"||a.kind==="warning"||a.kind==="success");
  return <>
    <section className="agent-hero"><div className="agent-hero-main"><div className="agent-avatar" aria-hidden="true"><Bot size={26}/><span className={`agent-status-dot ${enabled?"":"paused"}`}/></div><div><div className="agent-title-row"><h2>Project Coordinator</h2><span className={`agent-status ${enabled?"":"paused"}`}><i/>{enabled?"Agent active":"Agent paused"}</span></div><p>Review blockers and prepare follow-ups from the task data already in this workspace.</p><div className="agent-capabilities"><span><Check size={13} aria-hidden="true"/> Follow-up queue</span><span><Check size={13} aria-hidden="true"/> Blocker detection</span><span><Check size={13} aria-hidden="true"/> Status interpretation</span></div></div></div><div className="agent-hero-controls"><span>Coordinator</span><button className={`toggle ${enabled?"on":""}`} onClick={()=>{setEnabled(!enabled);setToast(enabled?"AI coordinator paused":"AI coordinator resumed");}} aria-label={`${enabled?"Pause":"Resume"} AI coordinator`} aria-pressed={enabled}><i/></button></div></section>
    <div className="agent-stat-grid"><div className="panel agent-stat"><span className="agent-stat-icon purple" aria-hidden="true"><MessageCircle size={16}/></span><div><span>Tasks needing follow-up</span><strong>{Math.min(3,pending.length)}</strong><small>Based on open tasks</small></div></div><div className="panel agent-stat"><span className="agent-stat-icon orange" aria-hidden="true"><AlertCircle size={16}/></span><div><span>Open blockers</span><strong>{tasks.filter(t=>t.status==="Blocked").length}</strong><small>Require attention</small></div></div><div className="panel agent-stat"><span className="agent-stat-icon green" aria-hidden="true"><CheckCheck size={16}/></span><div><span>Activity entries</span><strong>{activity.length}</strong><small>Current demo feed</small></div></div><div className="panel agent-stat"><span className="agent-stat-icon blue" aria-hidden="true"><Zap size={16}/></span><div><span>Completed tasks</span><strong>{tasks.filter(t=>t.status==="Completed").length}</strong><small>From current task list</small></div></div></div>
    <div className="coordinator-layout"><section className="panel coordinator-main"><div className="panel-heading"><div><h3>Coordination workspace</h3><p>Choose a task to prepare a follow-up, or review coordinator activity.</p></div><span className="demo-badge"><span/> DEMO MODE</span></div><div className="tab-strip" role="tablist" aria-label="Coordinator workspace"><button role="tab" aria-selected={tab==="Follow-up queue"} className={tab==="Follow-up queue"?"selected":""} onClick={()=>setTab("Follow-up queue")}>Pending coordination</button><button role="tab" aria-selected={tab==="Recent decisions"} className={tab==="Recent decisions"?"selected":""} onClick={()=>setTab("Recent decisions")}>Recent activity</button></div>
      {tab==="Follow-up queue"?(pending.length ? <div className="followup-list">{pending.slice(0,4).map((t,i)=><article className="followup-card" key={t.id}><div className="followup-card-top"><span className={`followup-priority ${t.status==="Blocked"?"urgent":i===0?"soon":"normal"}`}>{t.status==="Blocked"?"BLOCKER DETECTED":i===0?"FOLLOW-UP DUE":"CHECK-IN SCHEDULED"}</span><span className="followup-time"><Clock3 size={12} aria-hidden="true"/>{i===0?"Due now":i===1?"In 2 hours":"Tomorrow"}</span></div><div className="followup-task"><Avatar initials={t.initials} color={avatarColor(t.initials)} size="small"/><div><strong>{t.title}</strong><small>{t.assignee} · {t.id}</small></div><StatusPill status={t.status}/></div><div className="message-preview"><Bot size={15} aria-hidden="true"/><p>{t.status==="Blocked"?`Hey ${t.assignee.split(" ")[0]}, I noticed a blocker on “${t.title}”. What do you need to get moving again?`: `Hey ${t.assignee.split(" ")[0]}! Quick check-in on “${t.title}” — what’s the latest progress, and are you blocked on anything?`}</p></div><div className="followup-card-actions"><span className="explain-link"><CircleHelp size={13} aria-hidden="true"/> Based on task status</span><button className="button button-secondary button-sm" onClick={()=>sendFollowup(t)} disabled={Boolean(messages[t.id])}>{messages[t.id]==="sending"?<><Clock3 size={13} aria-hidden="true"/> Sending…</>:messages[t.id]==="sent"?<><Check size={13} aria-hidden="true"/> Sent</>:messages[t.id]==="demo"?<><Check size={13} aria-hidden="true"/> Queued in demo</>:<><Send size={13} aria-hidden="true"/> {apiState==="connected"?"Send follow-up":"Queue follow-up"}</>}</button></div></article>)}</div> : <div className="coordinator-empty"><MessageCircle size={22} aria-hidden="true"/><strong>No open tasks need coordination</strong><p>The queue will reflect current task statuses when work is available.</p></div>) : (recentActivity.length ? <div className="decision-list">{recentActivity.map(a=><ActivityItem key={a.id} item={a}/>)}</div> : <div className="coordinator-empty"><Activity size={22} aria-hidden="true"/><strong>No coordinator activity yet</strong><p>Actions prepared in this demo session will appear here.</p></div>)}
    </section><aside className="panel agent-settings"><div className="panel-heading"><div><h3>Coordinator controls</h3><p>Change how follow-ups are prepared in this session.</p></div><SlidersHorizontal size={17} aria-hidden="true"/></div><div className="setting-row"><div><strong>Automatic follow-ups</strong><p>Prepare reminders for stale tasks.</p></div><button className={`toggle ${enabled?"on":""}`} onClick={()=>setEnabled(!enabled)} aria-label={`${enabled?"Disable":"Enable"} automatic follow-ups`} aria-pressed={enabled}><i/></button></div><div className="setting-row"><div><strong>Auto-update task status</strong><p>Apply clear updates from replies.</p></div><button className={`toggle ${autoStatus?"on":""}`} onClick={()=>setAutoStatus(!autoStatus)} aria-label={`${autoStatus?"Disable":"Enable"} automatic task status updates`} aria-pressed={autoStatus}><i/></button></div><div className="setting-row"><div><strong>Respect quiet hours</strong><p>Avoid preparing late-night messages.</p></div><button className={`toggle ${quietHours?"on":""}`} onClick={()=>setQuietHours(!quietHours)} aria-label={`${quietHours?"Disable":"Enable"} quiet hours`} aria-pressed={quietHours}><i/></button></div><label className="field-label cadence-label">Follow-up cadence<select aria-label="Follow-up cadence" value={cadence} onChange={e=>setCadence(e.target.value)}><option>Every 12 hours</option><option>Every 24 hours</option><option>Every 48 hours</option><option>Every 3 days</option></select></label><div className="settings-note"><ShieldCheck size={15} aria-hidden="true"/><p>Suggestions are reviewed by frontend demo rules. No message is sent and no task data changes until backend integration is available.</p></div><button className="button button-primary full-button" onClick={()=>setToast("Agent preferences saved for this demo.")}>Save preferences</button></aside></div>
  </>;
}
function ActivityLog({activity}) {
  const [filter,setFilter]=useState("All activity");
  const visible=activity.filter(a=>filter==="All activity"||(filter==="AI coordinator"&&a.kind==="bot")||(filter==="Task updates"&&a.kind!=="bot"));
  return <><div className="activity-intro"><div><h2>Keep the thread of work</h2><p>Review task changes and coordinator actions, newest first.</p></div><span className="activity-demo-note"><ShieldCheck size={14} aria-hidden="true"/> Demo activity</span></div><div className="filter-bar activity-filter-bar"><div className="search-field"><Search size={16} aria-hidden="true"/><input aria-label="Search activity" placeholder="Search activity..." onChange={()=>{}}/></div><label className="sr-only" htmlFor="activity-filter">Filter activity</label><select id="activity-filter" aria-label="Filter activity" value={filter} onChange={e=>setFilter(e.target.value)}><option>All activity</option><option>AI coordinator</option><option>Task updates</option></select><span className="audit-note"><ShieldCheck size={14} aria-hidden="true"/> Activity history</span></div><section className="panel audit-panel"><div className="panel-heading"><div><h3>Workspace timeline</h3><p>Task changes and coordinator actions, newest first</p></div><span className="soft-tag">{visible.length} event{visible.length === 1 ? "" : "s"}</span></div>{visible.length ? <div className="audit-timeline">{visible.map(a=><div className="audit-row" key={a.id}><div className={`audit-icon ${a.kind}`} aria-hidden="true"><Activity size={15}/></div><div className="audit-body"><div className="audit-title-line"><strong>{a.title}</strong><span className={`activity-kind ${a.kind}`}>{activityKindLabel(a.kind)}</span></div><p>{a.detail}</p><small>{a.time} · CampusConnect</small></div><button className="row-more" aria-label={`Open actions for ${a.title}`}><MoreHorizontal size={17} aria-hidden="true"/></button></div>)}</div> : <EmptyOverviewState icon={Activity} title="No activity matches this filter" detail="Choose another activity filter to see workspace updates."/>}</section></>;
}
function activityKindLabel(kind) {
  return kind === "bot" ? "AI coordinator" : kind === "warning" ? "Attention" : kind === "success" ? "Completed" : "Task update";
}
function SettingsPage({aiEnabled,setAiEnabled,setToast,theme,setTheme}) {
  const [name,setName]=useState("CampusConnect");
  const [description,setDescription]=useState("Student collaboration, without the chaos.");
  const [reminders,setReminders]=useState(true);
  const [quiet,setQuiet]=useState(true);
  return <div className="settings-layout"><section className="panel settings-form-panel"><div className="settings-section-heading"><div><h3>Workspace details</h3><p>Edit the information shown for this project space.</p></div><ClipboardList size={17} aria-hidden="true"/></div><div className="settings-fields"><label className="field-label">Workspace name<input value={name} onChange={e=>setName(e.target.value)}/></label><label className="field-label">Project description<textarea rows="3" value={description} onChange={e=>setDescription(e.target.value)}/></label></div><div className="settings-divider"/><div className="settings-section-heading"><div><h3>Appearance</h3><p>Choose the surface treatment for this workspace.</p></div><Settings size={17} aria-hidden="true"/></div><div className="settings-fields appearance-setting"><label className="field-label" htmlFor="theme-select">Theme<select id="theme-select" aria-label="Theme" value={theme} onChange={e=>setTheme(e.target.value)}><option value="dark">Dark</option><option value="light">Light</option></select></label><p className="settings-inline-note">Your choice is saved in this browser and applies immediately.</p></div><div className="settings-divider"/><div className="settings-section-heading"><div><h3>AI coordinator</h3><p>Set the guardrails for follow-up preparation.</p></div><Bot size={18} aria-hidden="true"/></div><div className="settings-controls"><div className="setting-row"><div><strong>Enable coordinator</strong><p>Allow the agent to prepare follow-ups and interpret updates.</p></div><button className={`toggle ${aiEnabled?"on":""}`} onClick={()=>setAiEnabled(!aiEnabled)} aria-label={`${aiEnabled?"Disable":"Enable"} coordinator`} aria-pressed={aiEnabled}><i/></button></div><div className="setting-row"><div><strong>Automatic reminders</strong><p>Prepare check-ins when tasks are stale.</p></div><button className={`toggle ${reminders?"on":""}`} onClick={()=>setReminders(!reminders)} aria-label={`${reminders?"Disable":"Enable"} automatic reminders`} aria-pressed={reminders}><i/></button></div><div className="setting-row"><div><strong>Quiet hours</strong><p>Respect your team's rest time.</p></div><button className={`toggle ${quiet?"on":""}`} onClick={()=>setQuiet(!quiet)} aria-label={`${quiet?"Disable":"Enable"} quiet hours`} aria-pressed={quiet}><i/></button></div></div><div className="settings-note"><ShieldCheck size={15} aria-hidden="true"/><p>These settings are stored in the browser session only. Persistent settings require backend endpoints.</p></div><button className="button button-primary" onClick={()=>setToast("Settings saved in the current demo session.")}>Save changes</button></section><aside className="panel integration-panel"><div className="settings-section-heading"><div><h3>Connection status</h3><p>Informational status for this frontend prototype.</p></div><ShieldCheck size={17} aria-hidden="true"/></div><div className="integration-list"><div className="integration-row"><span className="integration-logo google-chat" aria-hidden="true">G</span><div><strong>Google Chat</strong><small>Messaging platform</small></div><span className="integration-status not-connected"><i/> Not connected</span></div><div className="integration-row"><span className="integration-logo groq-logo" aria-hidden="true">✳</span><div><strong>Groq API</strong><small>AI reasoning engine</small></div><span className="integration-status not-connected"><i/> Not connected</span></div><div className="integration-row"><span className="integration-logo database-logo" aria-hidden="true"><ClipboardList size={16}/></span><div><strong>Task database</strong><small>Shared task storage</small></div><span className="integration-status demo"><i/> Demo data</span></div></div><div className="integration-disclaimer"><AlertCircle size={15} aria-hidden="true"/><p>These labels do not connect services. Configure credentials and backend event handlers before using real messages.</p></div></aside></div>;
}
function TaskDrawer({task,onClose,onUpdate}) {
  const [progress,setProgress]=useState(task.progress||0);
  const [blocker,setBlocker]=useState(task.blocker||"");
  const [description,setDescription]=useState(task.description||"");
  useEffect(()=>{setProgress(task.progress||0);setBlocker(task.blocker||"");setDescription(task.description||"")},[task.id]);
  return <div className="drawer-backdrop" onMouseDown={e=>{if(e.target===e.currentTarget)onClose()}}><aside className="task-drawer"><div className="drawer-top"><span className="eyebrow">{task.id} · CAMPUSCONNECT</span><button className="icon-btn" onClick={onClose} aria-label="Close task details"><X size={18} aria-hidden="true"/></button></div><div className="drawer-title-row"><span className={`task-priority priority-${task.priority.toLowerCase()}`}/><h2>{task.title}</h2></div><div className="drawer-pills"><StatusPill status={task.status}/><span className={`priority-label priority-text-${task.priority.toLowerCase()}`}>{task.priority} priority</span></div><div className="drawer-section"><label className="field-label">Description<textarea rows="3" value={description} onChange={e=>setDescription(e.target.value)}/></label></div><div className="drawer-section drawer-meta-grid"><div><span>Assignee</span><div className="assignee-cell"><Avatar initials={task.initials} color={avatarColor(task.initials)} size="small"/><strong>{task.assignee}</strong></div></div><div><span>Due date</span><strong className="drawer-due"><CalendarDays size={14}/>{task.dueDate}</strong></div></div><div className="drawer-section"><div className="progress-edit-head"><label className="field-label">Progress</label><strong>{progress}%</strong></div><input className="range-input" type="range" min="0" max="100" step="5" value={progress} onChange={e=>setProgress(Number(e.target.value))}/><ProgressBar value={progress}/></div><div className="drawer-section"><label className="field-label">Blocker or note<textarea rows="3" placeholder="What is preventing progress?" value={blocker} onChange={e=>setBlocker(e.target.value)}/></label></div><div className="drawer-section"><label className="field-label">Update status<select value={task.status} onChange={e=>onUpdate(task.id,{status:e.target.value,progress:e.target.value==="Completed"?100:progress,blocker})}>{Object.keys(statusMeta).map(s=><option key={s}>{s}</option>)}</select></label></div><div className="drawer-ai-note"><Bot size={16}/><div><strong>AI context</strong><p>The coordinator uses task details, deadline, recent updates and blockers to decide what to ask next.</p></div></div><div className="drawer-footer"><button className="button button-secondary" onClick={onClose}>Cancel</button><button className="button button-primary" onClick={()=>onUpdate(task.id,{progress,status:progress===100?"Completed":task.status,blocker,description})}><Check size={15}/> Save changes</button></div></aside></div>;
}
function avatarColor(initials) {
  const colors={AS:"purple",KM:"blue",RS:"pink",AP:"orange",NG:"green"};
  return colors[initials]||"blue";
}
