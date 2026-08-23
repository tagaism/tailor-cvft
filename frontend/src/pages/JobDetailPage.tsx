import { FormEvent, useEffect, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid2";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { ApiError, api, apiOrigin } from "../api";
import OpenableUrlField from "../components/OpenableUrlField";
import StatusChip from "../components/StatusChip";
import { JOB_NOT_FOUND, parseRouteId } from "../ids";
import type { Health, Job } from "../types";

export default function JobDetailPage() {
  const { id } = useParams();
  const jobId = parseRouteId(id);
  const navigate = useNavigate();
  const [job, setJob] = useState<Job | null>(null);
  const [statuses, setStatuses] = useState<Health["statuses"]>([]);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [saving, setSaving] = useState(false);
  const [building, setBuilding] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    api.health().then((data) => setStatuses(data.statuses)).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (jobId == null) return;
    let cancelled = false;
    setError("");
    setJob(null);
    api
      .job(jobId)
      .then((data) => {
        if (!cancelled) setJob(data);
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err instanceof ApiError && err.status === 404 ? JOB_NOT_FOUND : err.message || JOB_NOT_FOUND);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  function patch<K extends keyof Job>(key: K, value: Job[K]) {
    if (!job) return;
    setJob({ ...job, [key]: value });
  }

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!job) return;
    setSaving(true);
    setError("");
    try {
      const saved = await api.saveJob(job.id, {
        title: job.title,
        company: job.company_name,
        location: job.location,
        url: job.url,
        notes: job.notes,
        source_text: job.source_text,
        required_skills: job.required_skills,
        desired_skills: job.desired_skills,
        status: job.status,
        status_note: job.status_note,
      });
      setJob(saved);
      setFlash("Position saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setSaving(false);
    }
  }

  async function onBuild() {
    if (!job) return;
    setBuilding(true);
    setError("");
    setFlash("");
    try {
      const built = await api.buildJob(job.id);
      setJob(built);
      setFlash("Tailored pack is ready below.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Build failed.");
    } finally {
      setBuilding(false);
    }
  }

  async function onRefetch() {
    if (!job) return;
    setError("");
    try {
      setJob(await api.refetchJob(job.id));
      setFlash("Fetched the page again.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-fetch failed.");
    }
  }

  async function onDelete() {
    if (!job) return;
    await api.deleteJob(job.id);
    navigate("/jobs");
  }

  if (jobId == null) {
    return (
      <Alert severity="error">
        {JOB_NOT_FOUND} <RouterLink to="/jobs">Back to positions</RouterLink>
      </Alert>
    );
  }
  if (!job && error) {
    return (
      <Alert severity="error">
        {error} <RouterLink to="/jobs">Back to positions</RouterLink>
      </Alert>
    );
  }
  if (!job) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", py: 8 }}>
        <CircularProgress />
      </Box>
    );
  }

  const match = job.generation?.match;
  const canBuild = Boolean(job.profile_ready && job.source_text.trim());

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <Box>
          <Typography color="text.secondary">
            <RouterLink to="/jobs">Positions</RouterLink>
            {job.company_id ? (
              <>
                {" · "}
                <RouterLink to={`/companies/${job.company_id}`}>{job.company_name}</RouterLink>
              </>
            ) : null}
          </Typography>
          <Typography variant="h1">{job.title || "Untitled role"}</Typography>
          <Stack direction="row" alignItems="center" gap={1} sx={{ mt: 0.5 }} flexWrap="wrap">
            <StatusChip status={job.status} label={job.status_label} />
            <Typography color="text.secondary">
              {job.company_name || "Company unknown"}
              {job.location ? ` · ${job.location}` : ""}
              {job.source_host ? ` · ${job.source_host}` : ""}
            </Typography>
          </Stack>
        </Box>
        <Button color="error" variant="outlined" onClick={() => setConfirmDelete(true)}>
          Delete
        </Button>
      </Stack>

      {flash && <Alert severity="success">{flash}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}
      {!job.profile_ready && (
        <Alert severity="warning">
          Your profile is incomplete. <RouterLink to="/profile">Add your name and experience</RouterLink> before
          building a CV.
        </Alert>
      )}

      <Paper component="form" onSubmit={onSave} sx={{ p: 2.5 }}>
        <Typography variant="h2" sx={{ mb: 2 }}>
          Application
        </Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              select
              label="Status"
              value={job.status}
              onChange={(e) => patch("status", e.target.value as Job["status"])}
            >
              {statuses.map((item) => (
                <MenuItem key={item.value} value={item.value}>
                  {item.label} — {item.hint}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField label="Role location" value={job.location} onChange={(e) => patch("location", e.target.value)} />
          </Grid>
          <Grid size={12}>
            <TextField
              label="Status note"
              value={job.status_note}
              onChange={(e) => patch("status_note", e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField label="Title" value={job.title} onChange={(e) => patch("title", e.target.value)} />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              label="Company"
              value={job.company_name}
              onChange={(e) => patch("company_name", e.target.value)}
            />
          </Grid>
          <Grid size={12}>
            <OpenableUrlField value={job.url} onChange={(url) => patch("url", url)} />
          </Grid>
          <Grid size={12}>
            <TextField
              label="Notes to emphasize"
              multiline
              minRows={2}
              value={job.notes}
              onChange={(e) => patch("notes", e.target.value)}
            />
          </Grid>
          <Grid size={12}>
            <TextField
              label="Job description"
              multiline
              minRows={8}
              value={job.source_text}
              onChange={(e) => patch("source_text", e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              label="Required skills"
              multiline
              minRows={4}
              value={job.required_skills}
              onChange={(e) => patch("required_skills", e.target.value)}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              label="Desired skills"
              multiline
              minRows={4}
              value={job.desired_skills}
              onChange={(e) => patch("desired_skills", e.target.value)}
            />
          </Grid>
        </Grid>
        {job.scrape_warning && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            {job.scrape_warning}
          </Alert>
        )}
        <Stack direction="row" gap={1} sx={{ mt: 2 }}>
          <Button type="submit" variant="outlined" disabled={saving}>
            {saving ? "Saving…" : "Save position"}
          </Button>
          {job.url && (
            <Button type="button" onClick={onRefetch}>
              Re-fetch URL
            </Button>
          )}
        </Stack>
      </Paper>

      <Paper sx={{ p: 2.5 }}>
        <Typography variant="h2">Build tailored pack</Typography>
        <Typography color="text.secondary" sx={{ my: 1 }}>
          Uses your saved profile and this job text. Local models often take 3–10 minutes. Leave this tab open.
        </Typography>
        <Button variant="contained" onClick={onBuild} disabled={!canBuild || building} startIcon={building ? <CircularProgress size={16} /> : undefined}>
          {building ? "LM Studio is writing…" : "Build tailored pack"}
        </Button>
      </Paper>

      {job.generation && (
        <>
          <Paper sx={{ p: 2.5 }} id="results">
            <Typography variant="h2">Match analysis</Typography>
            <Typography color="text.secondary" sx={{ mb: 2 }}>
              Built {job.generation.created_at?.slice(0, 16).replace("T", " ")} UTC · {job.generation.model_name}
            </Typography>
            {match?.matched_skills.length ? (
              <>
                <Typography variant="subtitle2">Matched skills</Typography>
                <Stack direction="row" gap={0.75} flexWrap="wrap" sx={{ mb: 1.5 }}>
                  {match.matched_skills.map((skill) => (
                    <Chip key={skill} label={skill} color="success" />
                  ))}
                </Stack>
              </>
            ) : null}
            {match?.missing_skills.length ? (
              <>
                <Typography variant="subtitle2">Gaps vs the posting</Typography>
                <Stack direction="row" gap={0.75} flexWrap="wrap" sx={{ mb: 1.5 }}>
                  {match.missing_skills.map((skill) => (
                    <Chip key={skill} label={skill} color="error" variant="outlined" />
                  ))}
                </Stack>
              </>
            ) : null}
            {match?.keyword_coverage.length ? (
              <>
                <Typography variant="subtitle2">Keyword coverage</Typography>
                <Stack direction="row" gap={0.75} flexWrap="wrap" sx={{ mb: 1.5 }}>
                  {match.keyword_coverage.map((item) => (
                    <Chip
                      key={item.keyword}
                      label={item.keyword}
                      color={item.present ? "success" : "error"}
                      variant={item.present ? "filled" : "outlined"}
                    />
                  ))}
                </Stack>
              </>
            ) : null}
            {["emphasis", "gaps", "talking_points"].map((key) => {
              const items = match?.[key as "emphasis" | "gaps" | "talking_points"] || [];
              const titles = {
                emphasis: "What was emphasized",
                gaps: "Honest gaps",
                talking_points: "Talking points",
              };
              if (!items.length) return null;
              return (
                <Box key={key} sx={{ mb: 1.5 }}>
                  <Typography variant="subtitle2">{titles[key as keyof typeof titles]}</Typography>
                  <ul>
                    {items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </Box>
              );
            })}
          </Paper>

          <Paper sx={{ p: 2.5 }}>
            <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1} sx={{ mb: 1 }}>
              <Box>
                <Typography variant="h2">Tailored CV</Typography>
                <Typography color="text.secondary">
                  Click the intro or a bullet in the preview to edit. Use B / I. Click outside to save.
                </Typography>
              </Box>
              <Stack direction="row" gap={1}>
                <Button href={`${apiOrigin}/jobs/${job.id}/preview`} target="_blank" rel="noreferrer" variant="outlined">
                  Open preview
                </Button>
                <Button href={`${apiOrigin}/jobs/${job.id}/pdf`} variant="contained">
                  Download PDF
                </Button>
              </Stack>
            </Stack>
            <Box
              component="iframe"
              title="Tailored CV"
              src={`${apiOrigin}/jobs/${job.id}/preview`}
              sx={{ width: "100%", height: 900, border: 0, bgcolor: "background.default" }}
            />
          </Paper>

          <Paper sx={{ p: 2.5 }}>
            <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1} sx={{ mb: 1 }}>
              <Box>
                <Typography variant="h2">Cover letter</Typography>
                <Typography color="text.secondary">
                  Click the letter to edit. Use B / I. Click outside to save.
                </Typography>
              </Box>
              <Stack direction="row" gap={1}>
                <Button
                  href={`${apiOrigin}/jobs/${job.id}/cover-letter`}
                  target="_blank"
                  rel="noreferrer"
                  variant="outlined"
                >
                  Open preview
                </Button>
                <Button href={`${apiOrigin}/jobs/${job.id}/cover-letter/pdf`} variant="contained">
                  Download PDF
                </Button>
              </Stack>
            </Stack>
            <Box
              component="iframe"
              title="Cover letter"
              src={`${apiOrigin}/jobs/${job.id}/cover-letter`}
              sx={{ width: "100%", height: 640, border: 0, bgcolor: "background.default" }}
            />
          </Paper>
        </>
      )}

      <Dialog open={confirmDelete} onClose={() => setConfirmDelete(false)}>
        <DialogTitle>Delete this position?</DialogTitle>
        <DialogContent>
          <DialogContentText>This also deletes generated CVs for the role.</DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmDelete(false)}>Cancel</Button>
          <Button color="error" onClick={onDelete}>
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}
