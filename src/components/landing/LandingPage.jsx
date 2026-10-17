import React from "react";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  Bot,
  CheckCircle2,
  CircleDot,
  Layers3,
  Send,
  Sparkles,
  Users,
  Workflow,
} from "lucide-react";
import "./LandingPage.css";

const features = [
  {
    number: "01",
    title: "Organize the chaos",
    description:
      "Bring project tasks, teammates, and deadlines into one clear workspace.",
    icon: Layers3,
  },
  {
    number: "02",
    title: "Delegate with clarity",
    description:
      "Make ownership visible and help everyone understand what needs to happen next.",
    icon: Workflow,
  },
  {
    number: "03",
    title: "Stay in sync",
    description:
      "Track progress in your workspace and receive Slack updates when configured.",
    icon: Send,
  },
];

export default function LandingPage({ onGetStarted }) {
  const goToWorkspace = () => {
    if (onGetStarted) {
      onGetStarted();
      return;
    }
    document.getElementById("workflow")?.scrollIntoView({ behavior: "smooth" });
  };

  return (
    <main className="landing">
      <nav className="landing-nav" aria-label="Main navigation">
        <a className="brand" href="#home" aria-label="DelegatorAI home">
          <span className="brand-mark">d.</span>
          <span>delegator<span className="brand-muted">ai</span></span>
        </a>

        <div className="nav-links">
          <a href="#features">Features</a>
          <a href="#workflow">How it works</a>
        </div>

        <button className="nav-cta" onClick={goToWorkspace}>
          Open workspace <ArrowUpRight size={15} aria-hidden="true" />
        </button>
      </nav>

      <section className="hero" id="home">
        <div className="hero-glow" aria-hidden="true" />
        <div className="hero-copy">
          <div className="eyebrow">
            <span className="status-dot" />
            YOUR AI PROJECT COORDINATOR
          </div>

          <h1>
            Less chaos.
            <br />
            <span className="gradient-text">More progress.</span>
          </h1>

          <p className="hero-description">
            Keep your team moving in the same direction. Delegate tasks,
            coordinate work, and make project progress easier to see.
          </p>

          <div className="hero-actions">
            <button className="button-primary" onClick={goToWorkspace}>
              Explore workspace <ArrowUpRight size={16} aria-hidden="true" />
            </button>
            <a className="button-secondary" href="#workflow">
              See how it works <ArrowDownRight size={16} aria-hidden="true" />
            </a>
          </div>

          <div className="hero-footnote">
            Built for teams that have things to ship.
          </div>
        </div>

        <div
          className="visual-stage"
          aria-label="Illustration of AI coordinating project tasks"
        >
          <div className="orbit orbit-one" aria-hidden="true" />
          <div className="orbit orbit-two" aria-hidden="true" />

          <div className="floating-card task-card">
            <div className="mini-card-top">
              <span className="mini-icon"><CheckCircle2 size={16} /></span>
              <span className="mini-label">TASK ASSIGNMENT</span>
            </div>
            <strong>Finalize project UI</strong>
            <div className="task-person">
              <span className="avatar">D</span>
              <span>Design team</span>
              <span className="task-state">In progress</span>
            </div>
          </div>

          <div className="ai-core">
            <div className="core-ring ring-a" aria-hidden="true" />
            <div className="core-ring ring-b" aria-hidden="true" />
            <Sparkles className="core-symbol" size={48} strokeWidth={1.4} />
            <span className="core-caption">AI COORDINATOR</span>
          </div>

          <div className="floating-card update-card">
            <span className="update-dot" />
            <div>
              <strong>Project update</strong>
              <p>Tasks organized for your team</p>
            </div>
          </div>

          <div className="floating-card slack-card">
            <span className="slack-symbol"><Send size={17} /></span>
            <div>
              <strong>Team notifications</strong>
              <p>Slack · when connected</p>
            </div>
          </div>
        </div>
      </section>

      <section className="features-section" id="features">
        <div className="section-heading">
          <span className="eyebrow">A BETTER WAY TO WORK</span>
          <h2>Less managing. More making.</h2>
          <p>
            The essentials your team needs, without another overwhelming dashboard.
          </p>
        </div>

        <div className="feature-grid">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <article className="feature-card" key={feature.number}>
                <div className="feature-card-top">
                  <span className="feature-icon"><Icon size={19} /></span>
                  <span className="feature-number">{feature.number}</span>
                </div>
                <h3>{feature.title}</h3>
                <p>{feature.description}</p>
              </article>
            );
          })}
        </div>
      </section>

      <section className="workflow-section" id="workflow">
        <div>
          <span className="eyebrow">SIMPLE BY DESIGN</span>
          <h2>From scattered work to shared progress.</h2>
          <p className="workflow-intro">
            One clear flow for keeping your team aligned from kickoff to delivery.
          </p>
        </div>

        <div className="workflow-steps">
          <div><span>01</span><strong>Create a project</strong><CircleDot size={17} /></div>
          <div><span>02</span><strong>Coordinate tasks</strong><Users size={17} /></div>
          <div><span>03</span><strong>Track the progress</strong><CheckCircle2 size={17} /></div>
        </div>
      </section>

      <section className="closing-cta">
        <div className="closing-glow" aria-hidden="true" />
        <span className="eyebrow">READY WHEN YOUR TEAM IS</span>
        <h2>Make teamwork feel lighter.</h2>
        <p>Your next project deserves less chaos.</p>
        <button className="button-primary" onClick={goToWorkspace}>
          Explore DelegatorAI <ArrowRight size={16} aria-hidden="true" />
        </button>
      </section>

      <footer className="landing-footer">
        <a className="brand" href="#home">
          <span className="brand-mark">d.</span>
          <span>delegator<span className="brand-muted">ai</span></span>
        </a>
        <span>Built to help teams move forward.</span>
      </footer>
    </main>
  );
}
