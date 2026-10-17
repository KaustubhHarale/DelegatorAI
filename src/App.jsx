import React, { useMemo, useState } from "react";
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
import LandingPage from "./components/landing/LandingPage.jsx";

const initialTasks = [
  { id: 1, title: "Design onboarding flow", project: "DelegatorAI", assignee: "Akhilesh K.", initials: "AK", due: "Today", status: "In progress" },
  { id: 2, title: "Set up Chat API endpoint", project: "DelegatorAI", assignee: "Harsh T.", initials: "HT", due: "Oct 19", status: "In progress" },
  { id: 3, title: "Write API integration tests", project: "Backend services", assignee: "Riya S.", initials: "RS", due: "Oct 20", status: "To do" },
  { id: 4, title: "Finalize component library", project: "DelegatorAI", assignee: "Kaustubh", initials: "KA", due: "Oct 21", status: "To do" },
  { id: 5, title: "Document project architecture", project: "Documentation", assignee: "Akhilesh K.", initials: "AK", due: "Oct 16", status: "Completed" },
];

const members = [
  { initials: "AK", name: "Akhilesh Kotwal", role: "Frontend developer", status: "Online" },
  { initials: "HT", name: "Harsh Tiwari", role: "Backend developer", status: "Working" },
  { initials: "RS", name: "Riya Sharma", role: "AI & integrations", status: "Online" },
  { initials: "KA", name: "Kaustubh", role: "Project member", status: "You" },
];

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
  const [tasks, setTasks] = useState(initialTasks);
  const [query, setQuery] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [newTask, setNewTask] = useState("");
  const completed = tasks.filter((task) => task.status === "Completed").length;
  const inProgress = tasks.filter((task) => task.status === "In progress").length;
  const visibleTasks = useMemo(
    () => tasks.filter((task) => `${task.title} ${task.project} ${task.assignee}`.toLowerCase().includes(query.toLowerCase())),
    [tasks, query],
  );
  const cycleTask = (id) => setTasks((current) => current.map((task) => task.id === id
    ? { ...task, status: task.status === "To do" ? "In progress" : task.status === "In progress" ? "Completed" : "To do" }
    : task));
  const createTask = (event) => {
    event.preventDefault();
    if (!newTask.trim()) return;
    setTasks((current) => [{ id: Date.now(), title: newTask.trim(), project: "DelegatorAI", assignee: "Kaustubh", initials: "KA", due: "Oct 22", status: "To do" }, ...current]);
    setNewTask("");
    setShowCreate(false);
  };

  return (
    <div className="workspace-shell">
      <aside className="workspace-sidebar">
        <a className="workspace-brand" href="#workspace"><span className="auth-brand-mark"><Sparkles size={18} /></span><span>Delegator<span>AI</span></span></a>
        <div className="workspace-label">WORKSPACE</div>
        <button className="workspace-nav active"><LayoutDashboard size={17} /> Overview</button>
        <button className="workspace-nav"><ListTodo size={17} /> My tasks <span className="nav-count">{tasks.filter((task) => task.status !== "Completed").length}</span></button>
        <button className="workspace-nav"><FileText size={17} /> Projects</button>
        <button className="workspace-nav"><Users size={17} /> Team</button>
        <div className="workspace-sidebar-bottom">
          <button className="workspace-nav"><CircleHelp size={17} /> Help & support</button>
          <button className="workspace-nav"><Settings2 size={17} /> Settings</button>
          <button className="signed-in-user" onClick={onSignOut}><span className="avatar">KA</span><span><strong>Kaustubh</strong><small>Sign out</small></span><ArrowUpRight size={15} /></button>
        </div>
      </aside>

      <main className="workspace-main">
        <header className="workspace-topbar">
          <div className="breadcrumbs">Workspace <span>/</span> <strong>Overview</strong></div>
          <div className="workspace-top-actions">
            <label className="workspace-search"><Search size={15} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tasks..." /></label>
            <button className="square-button" aria-label="Notifications"><Bell size={17} /></button>
            <span className="avatar">KA</span>
          </div>
        </header>

        <div className="workspace-content">
          <section className="workspace-welcome">
            <div><span className="auth-form-eyebrow">MONDAY, OCTOBER 19, 2026</span><h1>Good morning, Kaustubh</h1><p>Here’s what’s happening with your team today.</p></div>
            <button className="button-primary create-task-button" onClick={() => setShowCreate(true)}><Plus size={16} /> Create task</button>
          </section>

          <section className="workspace-panel task-overview">
            <div className="workspace-panel-heading"><div><h2>Task overview</h2><p>Keep track of what your team is working on.</p></div><span className="panel-count">{tasks.length} tasks</span></div>
            <div className="task-table-scroll"><table className="workspace-task-table"><thead><tr><th>TASK NAME</th><th>ASSIGNEE</th><th>DUE DATE</th><th>STATUS</th></tr></thead><tbody>
              {visibleTasks.map((task) => <tr key={task.id}><td><div className="workspace-task-name"><button className={`task-check ${task.status === "Completed" ? "checked" : ""}`} onClick={() => cycleTask(task.id)} aria-label={`Change ${task.title} status`}>{task.status === "Completed" && <Check size={12} />}</button><div><strong className={task.status === "Completed" ? "task-completed" : ""}>{task.title}</strong><small>{task.project}</small></div></div></td><td><span className="assignee"><span className="avatar">{task.initials}</span>{task.assignee}</span></td><td>{task.due}</td><td><button className={`task-status ${task.status.toLowerCase().replace(" ", "-")}`} onClick={() => cycleTask(task.id)}>{task.status}</button></td></tr>)}
            </tbody></table>{visibleTasks.length === 0 && <p className="no-tasks">No tasks match your search.</p>}</div>
            <div className="workspace-panel-footer">Showing {visibleTasks.length} of {tasks.length} tasks <button onClick={() => setShowCreate(true)}>Add a task <ArrowRight size={14} /></button></div>
          </section>

          <section className="workspace-panel members-panel">
            <div className="workspace-panel-heading"><div><h2>Team members</h2><p>4 people in your workspace</p></div><button className="text-button"><Users size={15} /> Team</button></div>
            <div className="member-list">{members.map((member) => <div className="member-row" key={member.initials}><span className="avatar">{member.initials}</span><span className="member-info"><strong>{member.name}</strong><small>{member.role}</small></span><span className={`member-status ${member.status.toLowerCase()}`}>{member.status}</span></div>)}</div>
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
            <div className="workspace-panel activity-panel"><div className="workspace-panel-heading"><div><h2>Recent activity</h2><p>A little progress goes a long way.</p></div><Activity size={17} /></div><div className="activity-list"><p><CheckCheck size={15} /><span><strong>Akhilesh</strong> completed Document project architecture<small>Today at 9:42 AM</small></span></p><p><MessageCircle size={15} /><span><strong>DelegatorAI</strong> suggested a priority review<small>Yesterday at 11:06 AM</small></span></p></div></div>
          </section>
          <section className="workspace-panel coordinator-panel"><div className="coordinator-heading"><span className="coordinator-icon"><Bot size={19} /></span><div><h2>AI coordinator</h2><p>Demo mode · backend not connected</p></div><span className="preview-badge">PREVIEW</span></div><p className="coordinator-message"><Sparkles size={15} /> Your team is making steady progress. Focus on the Chat API endpoint next.</p><div className="coordinator-input"><span>Ask your coordinator anything...</span><button aria-label="Send message"><Send size={15} /></button></div><small className="coordinator-disclaimer"><ShieldCheck size={13} /> Demo conversation only. No messages are sent.</small></section>
        </div>
      </main>

      {showCreate && <div className="modal-backdrop" onClick={() => setShowCreate(false)}><form className="create-modal" onSubmit={createTask} onClick={(event) => event.stopPropagation()}><div className="modal-title"><div><h2>Create a task</h2><p>Add work to your team’s queue.</p></div><button type="button" className="square-button" onClick={() => setShowCreate(false)} aria-label="Close"><X size={17} /></button></div><label htmlFor="new-task">Task name</label><input id="new-task" autoFocus value={newTask} onChange={(event) => setNewTask(event.target.value)} placeholder="e.g. Review API integration" required /><div className="modal-actions"><button type="button" className="auth-demo" onClick={() => setShowCreate(false)}>Cancel</button><button className="create-task-button" type="submit"><Plus size={15} /> Create task</button></div></form></div>}
    </div>
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
