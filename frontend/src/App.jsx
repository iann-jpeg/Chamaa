import { useState } from "react";

function EyeIcon({ hidden = false }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24">
      {hidden ? (
        <path d="M3 3l18 18M10.6 10.6a2 2 0 002.8 2.8M9.9 4.2A10.7 10.7 0 0112 4c6.5 0 10 8 10 8a18 18 0 01-3.1 4.1M6.2 6.2A18 18 0 002 12s3.5 8 10 8a9.8 9.8 0 004.2-.9" />
      ) : (
        <>
          <path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12Z" />
          <circle cx="12" cy="12" r="3" />
        </>
      )}
    </svg>
  );
}

function LoginApp({ root }) {
  const [showPassword, setShowPassword] = useState(false);
  const username = root.dataset.username || "";
  const formErrors = root.dataset.formErrors || "";
  const usernameErrors = root.dataset.usernameErrors || "";
  const passwordErrors = root.dataset.passwordErrors || "";
  const next = root.dataset.next || "";

  return (
    <div className="react-auth">
      <div className="auth-header">
        <span className="auth-kicker">MEMBER PORTAL</span>
        <h2>Sign in to CHAMAA</h2>
        <p>Use your username, email address or registered mobile number.</p>
      </div>
      <form className="auth-form" method="post" action={root.dataset.action} noValidate>
        <input type="hidden" name="csrfmiddlewaretoken" value={root.dataset.csrf} />
        {formErrors && <div className="form-errors" role="alert">{formErrors}</div>}

        <label className="field-label" htmlFor="id_username">Username, email or mobile number</label>
        <div className="input-wrap">
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="M20 21a8 8 0 0 0-16 0M12 13a5 5 0 1 0 0-10 5 5 0 0 0 0 10Z" />
          </svg>
          <input
            id="id_username"
            name="username"
            type="text"
            defaultValue={username}
            autoComplete="username"
            placeholder="Username, email or mobile number"
          />
        </div>
        {usernameErrors && <div className="field-error">{usernameErrors}</div>}

        <div className="label-row">
          <label className="field-label" htmlFor="id_password">Password</label>
          <a href={root.dataset.passwordReset}>Forgot password?</a>
        </div>
        <div className="input-wrap password-wrap">
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="M6 10V8a6 6 0 0 1 12 0v2M4 10h16v11H4zM12 14v3" />
          </svg>
          <input
            id="id_password"
            name="password"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            placeholder="Password"
          />
          <button
            className="password-toggle"
            type="button"
            aria-label={showPassword ? "Hide password" : "Show password"}
            aria-pressed={showPassword}
            onClick={() => setShowPassword((value) => !value)}
          >
            <EyeIcon hidden={showPassword} />
          </button>
        </div>
        {passwordErrors && <div className="field-error">{passwordErrors}</div>}

        <label className="check-row">
          <input type="checkbox" name="remember" />
          <span>Keep me signed in</span>
        </label>
        {next && <input type="hidden" name="next" value={next} />}
        <button className="primary-button" type="submit">
          <span>Sign in</span>
          <span aria-hidden="true">→</span>
        </button>
      </form>
      <p className="auth-switch">
        New to CHAMAA? <a href={root.dataset.register}>Create a member account</a>
      </p>
    </div>
  );
}

function LandingApp({ root }) {
  const links = {
    login: root.dataset.login,
    register: root.dataset.register,
  };

  return (
    <>
      <section className="hero">
        <div className="hero-orbit orbit-one"></div>
        <div className="hero-orbit orbit-two"></div>
        <div className="container hero-grid">
          <div className="hero-copy reveal visible">
            <span className="eyebrow"><span></span> Chama cycle management</span>
            <h1>Your Chama. Your Cycle. <em>Completely Automated.</em></h1>
            <p>Manage members, organize contributions, track payout positions and run your Chama cycles from one simple, secure platform.</p>
            <div className="hero-actions">
              <a className="button button-gold button-large" href={links.register}>Get Started <span aria-hidden="true">→</span></a>
              <a className="button button-outline-light button-large" href="#how-it-works">Explore How It Works</a>
            </div>
            <div className="hero-proof">
              <span className="proof-dot"></span>
              Built for clear records and transparent cycle administration
            </div>
          </div>
          <div className="dashboard-shell reveal visible" aria-label="Illustrative CHAMAA dashboard preview">
            <div className="mock-window">
              <div className="mock-topbar">
                <div className="mock-brand"><span>C</span> CHAMAA</div>
                <div className="mock-avatar" aria-hidden="true">SM</div>
              </div>
              <div className="mock-layout">
                <aside className="mock-sidebar" aria-hidden="true">
                  <span className="selected">⌂</span><span>◎</span><span>◫</span><span>↗</span><span>◷</span>
                </aside>
                <div className="mock-content">
                  <div className="mock-heading">
                    <div><small>Organization overview</small><strong>Good morning, Admin</strong></div>
                    <span>Sample data</span>
                  </div>
                  <div className="metric-grid">
                    <article><small>Active cycles</small><strong>3</strong><span className="trend">Live</span></article>
                    <article><small>Participants</small><strong>86</strong><span>Across cycles</span></article>
                    <article><small>Collected</small><strong>KES 48.2K</strong><span>This month</span></article>
                  </div>
                  <div className="mock-panels">
                    <article className="cycle-panel">
                      <div className="panel-title"><strong>Cycle progress</strong><small>Sample cycle</small></div>
                      <div className="cycle-name"><span>Weekly Growth</span><b>68%</b></div>
                      <div className="progress"><span style={{ width: "68%" }}></span></div>
                      <div className="cycle-stats"><div><small>Contributors</small><strong>24 / 30</strong></div><div><small>Next payout</small><strong>28 Nov</strong></div></div>
                    </article>
                    <article className="payout-panel">
                      <div className="panel-title"><strong>Upcoming payout</strong><small>Pending approval</small></div>
                      <div className="payout-person"><span>JN</span><div><strong>Jane N.</strong><small>Position #18</small></div></div>
                      <div className="payout-amount"><small>Scheduled amount</small><strong>KES 6,400</strong></div>
                    </article>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
}

export default function App() {
  const loginRoot = document.getElementById("react-login");
  const landingRoot = document.getElementById("react-landing");

  if (loginRoot) return <LoginApp root={loginRoot} />;
  if (landingRoot) return <LandingApp root={landingRoot} />;
  return null;
}
