"use client";

import {
  Activity,
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  ClipboardList,
  Clock3,
  FileAudio,
  KeyRound,
  LogOut,
  PhoneCall,
  RefreshCw,
  Search,
  ShieldCheck,
  Sparkles,
  Stethoscope,
  UserRoundCheck,
  UsersRound
} from "lucide-react";
import { FormEvent, useEffect, useMemo, useState } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8001";
const AUTH_STORAGE_KEY = "hospital_admin_token";

type DashboardSummary = {
  doctors: number;
  active_doctors: number;
  patients: number;
  appointments: number;
  todays_appointments: number;
  upcoming_appointments: number;
  booked_appointments: number;
  completed_appointments: number;
  cancelled_appointments: number;
  call_logs: number;
  calls_today: number;
};

type AppointmentStatus = "booked" | "confirmed" | "completed" | "cancelled" | "no_show" | "rescheduled";

type Appointment = {
  id: string;
  appointment_ref: string;
  patient_id: string;
  patient_name: string;
  patient_phone_masked: string;
  doctor_id: string;
  doctor_name: string;
  specialty: string;
  department: string;
  appointment_date: string;
  start_time: string;
  end_time: string;
  duration_minutes: number;
  reason_preview: string | null;
  status: AppointmentStatus;
  source: string;
  created_at: string;
};

type Doctor = {
  id: string;
  name: string;
  specialty: string;
  department: string;
  active: boolean;
  appointment_count: number;
};

type DoctorSchedule = {
  id: string;
  doctor_id: string;
  doctor_name: string;
  specialty: string;
  day_of_week: number;
  day_name: string;
  start_time: string;
  end_time: string;
  slot_duration_minutes: number;
  active: boolean;
};

type CallLog = {
  id: string;
  vapi_call_id: string;
  channel: string;
  status: string;
  caller_phone_masked: string | null;
  intent: string;
  resolution_status: string;
  escalated: boolean;
  escalation_reason: string | null;
  appointment_ref: string | null;
  has_summary: boolean;
  has_transcript: boolean;
  duration_seconds: number | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
};

type View = "overview" | "appointments" | "doctors" | "calls" | "vapi";

type LoginResponse = {
  access_token: string;
  role: string;
};

const statusOptions: AppointmentStatus[] = [
  "booked",
  "confirmed",
  "completed",
  "cancelled",
  "no_show",
  "rescheduled"
];

const navItems: Array<{ id: View; label: string; icon: typeof Activity }> = [
  { id: "overview", label: "Overview", icon: Activity },
  { id: "appointments", label: "Appointments", icon: CalendarClock },
  { id: "doctors", label: "Doctors", icon: Stethoscope },
  { id: "calls", label: "Call Logs", icon: PhoneCall },
  { id: "vapi", label: "Vapi Setup", icon: Sparkles }
];

const emptySummary: DashboardSummary = {
  doctors: 0,
  active_doctors: 0,
  patients: 0,
  appointments: 0,
  todays_appointments: 0,
  upcoming_appointments: 0,
  booked_appointments: 0,
  completed_appointments: 0,
  cancelled_appointments: 0,
  call_logs: 0,
  calls_today: 0
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong.";
}

async function apiFetch<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: "include"
  });

  if (!response.ok) {
    let message = `Request failed with ${response.status}`;
    try {
      const data = await response.json();
      message = data?.error?.message ?? data?.detail?.message ?? data?.detail ?? message;
    } catch {
      // Keep the HTTP status message when the backend returns no JSON body.
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

function formatDate(value: string | null): string {
  if (!value) {
    return "Not recorded";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: "numeric"
  }).format(new Date(value));
}

function formatDateTime(value: string | null): string {
  if (!value) {
    return "Not recorded";
  }
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date(value));
}

function formatTime(value: string): string {
  const [hour = 0, minute = 0] = value.split(":").map(Number);
  const date = new Date();
  date.setHours(hour, minute, 0, 0);
  return new Intl.DateTimeFormat("en", {
    hour: "numeric",
    minute: "2-digit"
  }).format(date);
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) {
    return "Open";
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds}s`;
}

function titleCase(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (char) => char.toUpperCase());
}

function endpoint(path: string): string {
  return `${API_BASE_URL}${path}`;
}

export default function AdminDashboard() {
  const [token, setToken] = useState<string>("");
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("change-this-password");
  const [activeView, setActiveView] = useState<View>("overview");
  const [summary, setSummary] = useState<DashboardSummary>(emptySummary);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [doctors, setDoctors] = useState<Doctor[]>([]);
  const [schedules, setSchedules] = useState<DoctorSchedule[]>([]);
  const [callLogs, setCallLogs] = useState<CallLog[]>([]);
  const [query, setQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<"all" | AppointmentStatus>("all");
  const [doctorFilter, setDoctorFilter] = useState("all");
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastSyncedAt, setLastSyncedAt] = useState<string | null>(null);

  const refreshData = async (activeToken = token) => {
    if (!activeToken) {
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const [summaryData, appointmentData, doctorData, scheduleData, callLogData] = await Promise.all([
        apiFetch<DashboardSummary>("/admin/dashboard/summary", activeToken),
        apiFetch<Appointment[]>("/admin/appointments", activeToken),
        apiFetch<Doctor[]>("/admin/doctors", activeToken),
        apiFetch<DoctorSchedule[]>("/admin/doctor-schedules", activeToken),
        apiFetch<CallLog[]>("/admin/call-logs", activeToken)
      ]);
      setSummary(summaryData);
      setAppointments(appointmentData);
      setDoctors(doctorData);
      setSchedules(scheduleData);
      setCallLogs(callLogData);
      setLastSyncedAt(new Date().toISOString());
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const storedToken = window.localStorage.getItem(AUTH_STORAGE_KEY);
    if (storedToken) {
      setToken(storedToken);
      void refreshData(storedToken);
    }
  }, []);

  const handleLogin = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAuthLoading(true);
    setError(null);
    try {
      const response = await apiFetch<LoginResponse>("/auth/login", undefined, {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      setToken(response.access_token);
      window.localStorage.setItem(AUTH_STORAGE_KEY, response.access_token);
      await refreshData(response.access_token);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    setToken("");
    setSummary(emptySummary);
    setAppointments([]);
    setDoctors([]);
    setSchedules([]);
    setCallLogs([]);
    setActiveView("overview");
  };

  const handleStatusChange = async (appointmentId: string, status: AppointmentStatus) => {
    const previousAppointments = appointments;
    setAppointments((current) =>
      current.map((appointment) => (appointment.id === appointmentId ? { ...appointment, status } : appointment))
    );
    try {
      const updated = await apiFetch<Appointment>(`/admin/appointments/${appointmentId}`, token, {
        method: "PATCH",
        body: JSON.stringify({ status })
      });
      setAppointments((current) =>
        current.map((appointment) => (appointment.id === appointmentId ? updated : appointment))
      );
      await refreshData();
    } catch (err) {
      setAppointments(previousAppointments);
      setError(getErrorMessage(err));
    }
  };

  const filteredAppointments = useMemo(() => {
    const search = query.trim().toLowerCase();
    return appointments.filter((appointment) => {
      const matchesStatus = statusFilter === "all" || appointment.status === statusFilter;
      const matchesDoctor = doctorFilter === "all" || appointment.doctor_id === doctorFilter;
      const matchesSearch =
        !search ||
        appointment.patient_name.toLowerCase().includes(search) ||
        appointment.appointment_ref.toLowerCase().includes(search) ||
        appointment.doctor_name.toLowerCase().includes(search) ||
        appointment.specialty.toLowerCase().includes(search) ||
        appointment.patient_phone_masked.toLowerCase().includes(search);
      return matchesStatus && matchesDoctor && matchesSearch;
    });
  }, [appointments, doctorFilter, query, statusFilter]);

  const todayAppointments = useMemo(() => {
    const today = new Date().toISOString().slice(0, 10);
    return appointments.filter((appointment) => appointment.appointment_date === today);
  }, [appointments]);

  const latestAppointments = appointments.slice(0, 6);
  const latestCalls = callLogs.slice(0, 5);
  const activeCallCount = callLogs.filter((call) => call.status !== "ended").length;

  if (!token) {
    return (
      <main className="login-shell">
        <section className="login-brand">
          <div className="brand-mark">
            <PhoneCall size={28} aria-hidden="true" />
          </div>
          <div>
            <p className="eyebrow">Official system console</p>
            <h1>AI Hospital Voice Receptionist</h1>
            <p className="login-copy">
              Review appointment records, Vapi call activity, doctor coverage, and routing readiness from one
              staff dashboard.
            </p>
          </div>
          <div className="signal-row">
            <span>
              <ShieldCheck size={18} aria-hidden="true" />
              Protected admin API
            </span>
            <span>
              <FileAudio size={18} aria-hidden="true" />
              Vapi Web Calls ready
            </span>
          </div>
        </section>

        <section className="login-panel" aria-label="Admin login">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">Staff access</p>
              <h2>Sign in</h2>
            </div>
            <KeyRound size={22} aria-hidden="true" />
          </div>

          <form onSubmit={handleLogin} className="login-form">
            <label>
              Email
              <input value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" />
            </label>
            <label>
              Password
              <input
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="current-password"
              />
            </label>
            {error ? (
              <div className="error-banner">
                <AlertCircle size={18} aria-hidden="true" />
                {error}
              </div>
            ) : null}
            <button className="primary-button" type="submit" disabled={authLoading}>
              {authLoading ? <RefreshCw className="spin" size={18} aria-hidden="true" /> : <ShieldCheck size={18} aria-hidden="true" />}
              {authLoading ? "Signing in" : "Open dashboard"}
            </button>
          </form>
        </section>
      </main>
    );
  }

  return (
    <main className="dashboard-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="brand-mark small">
            <PhoneCall size={22} aria-hidden="true" />
          </div>
          <div>
            <strong>Hospital AI</strong>
            <span>Reception console</span>
          </div>
        </div>

        <nav className="nav-list" aria-label="Dashboard sections">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={activeView === item.id ? "nav-item active" : "nav-item"}
                type="button"
                onClick={() => setActiveView(item.id)}
              >
                <Icon size={18} aria-hidden="true" />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="api-pill">
            <span className="status-dot" />
            {API_BASE_URL.replace(/^https?:\/\//, "")}
          </div>
          <button className="ghost-button full" type="button" onClick={handleLogout}>
            <LogOut size={17} aria-hidden="true" />
            Sign out
          </button>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">{activeView === "vapi" ? "Integration readiness" : "Live operations"}</p>
            <h1>{navItems.find((item) => item.id === activeView)?.label}</h1>
          </div>
          <div className="topbar-actions">
            <div className="sync-state">
              <Clock3 size={16} aria-hidden="true" />
              {lastSyncedAt ? `Synced ${formatDateTime(lastSyncedAt)}` : "Not synced yet"}
            </div>
            <button className="ghost-button" type="button" onClick={() => void refreshData()} disabled={loading}>
              <RefreshCw className={loading ? "spin" : ""} size={17} aria-hidden="true" />
              Refresh
            </button>
          </div>
        </header>

        {error ? (
          <div className="error-banner workspace-error">
            <AlertCircle size={18} aria-hidden="true" />
            {error}
          </div>
        ) : null}

        {activeView === "overview" ? (
          <Overview
            summary={summary}
            todayAppointments={todayAppointments}
            latestAppointments={latestAppointments}
            latestCalls={latestCalls}
            activeCallCount={activeCallCount}
          />
        ) : null}

        {activeView === "appointments" ? (
          <AppointmentsView
            appointments={filteredAppointments}
            doctors={doctors}
            query={query}
            statusFilter={statusFilter}
            doctorFilter={doctorFilter}
            onQueryChange={setQuery}
            onStatusFilterChange={setStatusFilter}
            onDoctorFilterChange={setDoctorFilter}
            onStatusChange={handleStatusChange}
          />
        ) : null}

        {activeView === "doctors" ? <DoctorsView doctors={doctors} schedules={schedules} /> : null}

        {activeView === "calls" ? <CallLogsView callLogs={callLogs} /> : null}

        {activeView === "vapi" ? <VapiView /> : null}
      </section>
    </main>
  );
}

function Overview({
  summary,
  todayAppointments,
  latestAppointments,
  latestCalls,
  activeCallCount
}: {
  summary: DashboardSummary;
  todayAppointments: Appointment[];
  latestAppointments: Appointment[];
  latestCalls: CallLog[];
  activeCallCount: number;
}) {
  const stats = [
    { label: "Appointments", value: summary.appointments, detail: `${summary.todays_appointments} today`, icon: CalendarClock },
    { label: "Upcoming", value: summary.upcoming_appointments, detail: `${summary.booked_appointments} active`, icon: ClipboardList },
    { label: "Patients", value: summary.patients, detail: "Encrypted records", icon: UsersRound },
    { label: "Doctors", value: summary.active_doctors, detail: `${summary.doctors} total`, icon: Stethoscope },
    { label: "Calls", value: summary.call_logs, detail: `${summary.calls_today} today`, icon: PhoneCall },
    { label: "Open Calls", value: activeCallCount, detail: "Monitor status", icon: Activity }
  ];

  return (
    <div className="view-stack">
      <section className="stat-grid" aria-label="Dashboard summary">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <article className="stat-card" key={stat.label}>
              <div className="stat-icon">
                <Icon size={20} aria-hidden="true" />
              </div>
              <span>{stat.label}</span>
              <strong>{stat.value}</strong>
              <small>{stat.detail}</small>
            </article>
          );
        })}
      </section>

      <section className="overview-grid">
        <div className="panel">
          <PanelTitle icon={CalendarClock} title="Today" meta={`${todayAppointments.length} appointments`} />
          <div className="timeline-list">
            {todayAppointments.length ? (
              todayAppointments.map((appointment) => (
                <div className="timeline-row" key={appointment.id}>
                  <span>{formatTime(appointment.start_time)}</span>
                  <div>
                    <strong>{appointment.patient_name}</strong>
                    <small>
                      {appointment.doctor_name} - {appointment.specialty}
                    </small>
                  </div>
                  <StatusBadge status={appointment.status} />
                </div>
              ))
            ) : (
              <EmptyState label="No appointments scheduled today." />
            )}
          </div>
        </div>

        <div className="panel">
          <PanelTitle icon={ClipboardList} title="Recent Appointments" meta={`${latestAppointments.length} shown`} />
          <div className="compact-list">
            {latestAppointments.length ? (
              latestAppointments.map((appointment) => (
                <div className="compact-row" key={appointment.id}>
                  <div>
                    <strong>{appointment.appointment_ref}</strong>
                    <span>{appointment.patient_name}</span>
                  </div>
                  <small>
                    {formatDate(appointment.appointment_date)} at {formatTime(appointment.start_time)}
                  </small>
                </div>
              ))
            ) : (
              <EmptyState label="No appointment records yet." />
            )}
          </div>
        </div>

        <div className="panel wide">
          <PanelTitle icon={PhoneCall} title="Latest Calls" meta={`${latestCalls.length} shown`} />
          <div className="call-strip">
            {latestCalls.length ? (
              latestCalls.map((call) => (
                <div className="call-card" key={call.id}>
                  <div className="call-card-top">
                    <PhoneCall size={18} aria-hidden="true" />
                    <StatusPill value={call.status} />
                  </div>
                  <strong>{call.vapi_call_id}</strong>
                  <span>{titleCase(call.intent)}</span>
                  <small>{formatDateTime(call.created_at)}</small>
                </div>
              ))
            ) : (
              <EmptyState label="No call logs captured yet." />
            )}
          </div>
        </div>
      </section>
    </div>
  );
}

function AppointmentsView({
  appointments,
  doctors,
  query,
  statusFilter,
  doctorFilter,
  onQueryChange,
  onStatusFilterChange,
  onDoctorFilterChange,
  onStatusChange
}: {
  appointments: Appointment[];
  doctors: Doctor[];
  query: string;
  statusFilter: "all" | AppointmentStatus;
  doctorFilter: string;
  onQueryChange: (value: string) => void;
  onStatusFilterChange: (value: "all" | AppointmentStatus) => void;
  onDoctorFilterChange: (value: string) => void;
  onStatusChange: (appointmentId: string, status: AppointmentStatus) => void;
}) {
  return (
    <div className="view-stack">
      <section className="toolbar">
        <div className="search-box">
          <Search size={18} aria-hidden="true" />
          <input
            value={query}
            onChange={(event) => onQueryChange(event.target.value)}
            placeholder="Search patient, doctor, ref"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(event) => onStatusFilterChange(event.target.value as "all" | AppointmentStatus)}
          aria-label="Filter by status"
        >
          <option value="all">All statuses</option>
          {statusOptions.map((status) => (
            <option key={status} value={status}>
              {titleCase(status)}
            </option>
          ))}
        </select>
        <select
          value={doctorFilter}
          onChange={(event) => onDoctorFilterChange(event.target.value)}
          aria-label="Filter by doctor"
        >
          <option value="all">All doctors</option>
          {doctors.map((doctor) => (
            <option key={doctor.id} value={doctor.id}>
              {doctor.name}
            </option>
          ))}
        </select>
      </section>

      <section className="panel table-panel">
        <PanelTitle icon={CalendarClock} title="Appointment Records" meta={`${appointments.length} records`} />
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Reference</th>
                <th>Patient</th>
                <th>Doctor</th>
                <th>Date</th>
                <th>Time</th>
                <th>Reason</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {appointments.length ? (
                appointments.map((appointment) => (
                  <tr key={appointment.id}>
                    <td>
                      <strong>{appointment.appointment_ref}</strong>
                      <small>{appointment.source}</small>
                    </td>
                    <td>
                      <strong>{appointment.patient_name}</strong>
                      <small>{appointment.patient_phone_masked}</small>
                    </td>
                    <td>
                      <strong>{appointment.doctor_name}</strong>
                      <small>
                        {appointment.specialty} - {appointment.department}
                      </small>
                    </td>
                    <td>{formatDate(appointment.appointment_date)}</td>
                    <td>
                      {formatTime(appointment.start_time)}
                      <small>{appointment.duration_minutes} min</small>
                    </td>
                    <td className="reason-cell">{appointment.reason_preview ?? "Not recorded"}</td>
                    <td>
                      <select
                        value={appointment.status}
                        onChange={(event) => onStatusChange(appointment.id, event.target.value as AppointmentStatus)}
                        aria-label={`Status for ${appointment.appointment_ref}`}
                      >
                        {statusOptions.map((status) => (
                          <option key={status} value={status}>
                            {titleCase(status)}
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={7}>
                    <EmptyState label="No appointments match the current filters." />
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function DoctorsView({ doctors, schedules }: { doctors: Doctor[]; schedules: DoctorSchedule[] }) {
  return (
    <div className="view-stack">
      <section className="doctor-grid">
        {doctors.map((doctor) => (
          <article className="doctor-card" key={doctor.id}>
            <div className="doctor-avatar">
              <Stethoscope size={22} aria-hidden="true" />
            </div>
            <div>
              <strong>{doctor.name}</strong>
              <span>{doctor.specialty}</span>
              <small>{doctor.department}</small>
            </div>
            <div className="doctor-count">
              <span>{doctor.appointment_count}</span>
              <small>appointments</small>
            </div>
          </article>
        ))}
      </section>

      <section className="panel table-panel">
        <PanelTitle icon={Clock3} title="Clinic Schedule" meta={`${schedules.length} schedule blocks`} />
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Doctor</th>
                <th>Specialty</th>
                <th>Day</th>
                <th>Hours</th>
                <th>Slot</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((schedule) => (
                <tr key={schedule.id}>
                  <td>
                    <strong>{schedule.doctor_name}</strong>
                  </td>
                  <td>{schedule.specialty}</td>
                  <td>{schedule.day_name}</td>
                  <td>
                    {formatTime(schedule.start_time)} - {formatTime(schedule.end_time)}
                  </td>
                  <td>{schedule.slot_duration_minutes} min</td>
                  <td>{schedule.active ? <StatusPill value="Active" /> : <StatusPill value="Inactive" muted />}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function CallLogsView({ callLogs }: { callLogs: CallLog[] }) {
  return (
    <section className="panel table-panel">
      <PanelTitle icon={PhoneCall} title="Vapi Call Logs" meta={`${callLogs.length} records`} />
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Call ID</th>
              <th>Caller</th>
              <th>Intent</th>
              <th>Channel</th>
              <th>Status</th>
              <th>Resolution</th>
              <th>Escalation</th>
              <th>Appointment</th>
              <th>Artifacts</th>
              <th>Duration</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {callLogs.length ? (
              callLogs.map((call) => (
                <tr key={call.id}>
                  <td>
                    <strong>{call.vapi_call_id}</strong>
                  </td>
                  <td>{call.caller_phone_masked ?? "Not provided"}</td>
                  <td>{titleCase(call.intent)}</td>
                  <td>{call.channel}</td>
                  <td>
                    <StatusPill value={call.status} />
                  </td>
                  <td>
                    <StatusPill value={call.resolution_status} muted={call.resolution_status === "open"} />
                  </td>
                  <td>
                    {call.escalated ? (
                      <span className="escalation-cell">
                        <StatusPill value="Escalated" />
                        <small>{call.escalation_reason ?? "Human follow-up needed"}</small>
                      </span>
                    ) : (
                      <StatusPill value="No" muted />
                    )}
                  </td>
                  <td>{call.appointment_ref ?? "None"}</td>
                  <td>
                    <div className="artifact-row">
                      <span className={call.has_summary ? "artifact active" : "artifact"}>Summary</span>
                      <span className={call.has_transcript ? "artifact active" : "artifact"}>Transcript</span>
                    </div>
                  </td>
                  <td>{formatDuration(call.duration_seconds)}</td>
                  <td>{formatDateTime(call.created_at)}</td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={11}>
                  <EmptyState label="No call logs have been stored yet." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function VapiView() {
  const tools = [
    {
      name: "lookupCallerHistory",
      method: "POST",
      url: endpoint("/vapi/tools/lookup-caller-history"),
      body: '{ "phone": "+923001234567", "vapi_call_id": "..." }'
    },
    {
      name: "classifyCallIntent",
      method: "POST",
      url: endpoint("/vapi/tools/classify-call-intent"),
      body: '{ "utterance": "I want to book an appointment", "vapi_call_id": "..." }'
    },
    {
      name: "matchDoctorBySymptoms",
      method: "POST",
      url: endpoint("/vapi/tools/match-doctor"),
      body: '{ "symptoms": "eye pain and blurry vision" }'
    },
    {
      name: "checkAvailability",
      method: "POST",
      url: endpoint("/vapi/tools/check-availability"),
      body: '{ "doctor_id": "...", "date": "2026-07-11" }'
    },
    {
      name: "bookAppointment",
      method: "POST",
      url: endpoint("/vapi/tools/book-appointment"),
      body: '{ "patient_name": "...", "phone": "...", "doctor_id": "...", "date": "...", "start_time": "10:00" }'
    }
  ];

  return (
    <div className="view-stack">
      <section className="panel">
        <PanelTitle icon={Sparkles} title="Vapi Tool Endpoints" meta="HTTPS tunnel required for live Vapi" />
        <div className="endpoint-list">
          {tools.map((tool) => (
            <article className="endpoint-row" key={tool.name}>
              <div>
                <strong>{tool.name}</strong>
                <span>{tool.method}</span>
              </div>
              <code>{tool.url}</code>
              <small>{tool.body}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="readiness-grid">
        <article className="readiness-card">
          <CheckCircle2 size={22} aria-hidden="true" />
          <strong>Bearer authorization</strong>
          <span>Configured in backend environment and pasted into Vapi request headers.</span>
        </article>
        <article className="readiness-card">
          <ShieldCheck size={22} aria-hidden="true" />
          <strong>PII handling</strong>
          <span>Patient fields and call artifacts stay encrypted at rest.</span>
        </article>
        <article className="readiness-card">
          <UserRoundCheck size={22} aria-hidden="true" />
          <strong>Booking safety</strong>
          <span>Database uniqueness and transactions prevent duplicate active bookings.</span>
        </article>
        <article className="readiness-card">
          <AlertCircle size={22} aria-hidden="true" />
          <strong>Urgent fallback</strong>
          <span>No-slot today/tomorrow responses recommend human receptionist handoff and next available dates.</span>
        </article>
      </section>

      <section className="panel">
        <PanelTitle icon={ShieldCheck} title="Assistant Guardrails" meta="Use inside the Vapi assistant prompt" />
        <div className="guardrail-grid">
          <div>
            <strong>No diagnosis</strong>
            <span>Route by symptoms only and avoid treatment advice.</span>
          </div>
          <div>
            <strong>No-slot flow</strong>
            <span>Offer next available date first, then human receptionist for urgent requests.</span>
          </div>
          <div>
            <strong>Emergency safety</strong>
            <span>For emergency symptoms, advise emergency department or local emergency services.</span>
          </div>
        </div>
      </section>
    </div>
  );
}

function PanelTitle({
  icon: Icon,
  title,
  meta
}: {
  icon: typeof Activity;
  title: string;
  meta: string;
}) {
  return (
    <div className="panel-title">
      <div>
        <Icon size={19} aria-hidden="true" />
        <h2>{title}</h2>
      </div>
      <span>{meta}</span>
    </div>
  );
}

function StatusBadge({ status }: { status: AppointmentStatus }) {
  return <span className={`status-badge status-${status}`}>{titleCase(status)}</span>;
}

function StatusPill({ value, muted = false }: { value: string; muted?: boolean }) {
  return <span className={muted ? "status-pill muted" : "status-pill"}>{titleCase(value)}</span>;
}

function EmptyState({ label }: { label: string }) {
  return <div className="empty-state">{label}</div>;
}
