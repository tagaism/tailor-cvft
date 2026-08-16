import { FormEvent, useEffect, useState } from "react";
import { Link as RouterLink, useNavigate, useSearchParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Grid from "@mui/material/Grid2";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import StatusChip from "../components/StatusChip";
import type { Health, Job } from "../types";

const emptyForm = {
  company_name: "",
  url: "",
  job_description: "",
  required_skills: "",
  desired_skills: "",
  notes: "",
};

export default function JobsPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const status = params.get("status") || "";
  const [jobs, setJobs] = useState<Job[]>([]);
  const [statuses, setStatuses] = useState<Health["statuses"]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.health().then((data) => setStatuses(data.statuses)).catch(() => undefined);
  }, []);

  useEffect(() => {
    setError("");
    api
      .jobs(status)
      .then((data) => setJobs(data.jobs))
      .catch((err: Error) => setError(err.message));
  }, [status]);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const job = await api.createJob(form);
      navigate(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the position.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h1">Positions</Typography>
        <Typography color="text.secondary">
          Companies and roles you are tracking. Build a tailored CV under each posting.
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      <Paper component="form" onSubmit={onCreate} sx={{ p: 2.5 }}>
        <Typography variant="h2" sx={{ mb: 1 }}>
          Add a job description
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 2 }}>
          Company name plus a job description is enough. A URL is optional — if LinkedIn blocks the fetch, keep the
          pasted description.
        </Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              label="Company name"
              value={form.company_name}
              onChange={(e) => setForm({ ...form, company_name: e.target.value })}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              label="Job URL"
              type="url"
              value={form.url}
              onChange={(e) => setForm({ ...form, url: e.target.value })}
            />
          </Grid>
          <Grid size={12}>
            <TextField
              label="Job description"
              multiline
              minRows={5}
              value={form.job_description}
              onChange={(e) => setForm({ ...form, job_description: e.target.value })}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              label="Required skills"
              multiline
              minRows={3}
              placeholder="One skill per line"
              value={form.required_skills}
              onChange={(e) => setForm({ ...form, required_skills: e.target.value })}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              label="Desired skills"
              multiline
              minRows={3}
              placeholder="One skill per line"
              value={form.desired_skills}
              onChange={(e) => setForm({ ...form, desired_skills: e.target.value })}
            />
          </Grid>
          <Grid size={12}>
            <TextField
              label="Notes to emphasize"
              multiline
              minRows={2}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </Grid>
        </Grid>
        <Button type="submit" variant="contained" sx={{ mt: 2 }} disabled={saving}>
          {saving ? "Saving…" : "Save position"}
        </Button>
      </Paper>

      <Stack direction="row" flexWrap="wrap" gap={1}>
        <Chip
          label="All"
          color={!status ? "primary" : "default"}
          variant={!status ? "filled" : "outlined"}
          onClick={() => setParams({})}
        />
        {statuses.map((item) => (
          <Chip
            key={item.value}
            label={item.label}
            color={status === item.value ? "primary" : "default"}
            variant={status === item.value ? "filled" : "outlined"}
            onClick={() => setParams({ status: item.value })}
          />
        ))}
      </Stack>

      <Grid container spacing={2}>
        {jobs.map((job) => (
          <Grid key={job.id} size={{ xs: 12, md: 6 }}>
            <Card>
              <CardActionArea component={RouterLink} to={`/jobs/${job.id}`}>
                <CardContent>
                  <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mb: 1 }}>
                    <StatusChip status={job.status} label={job.status_label} />
                    <Chip label={job.has_generation ? "CV ready" : "No CV"} color={job.has_generation ? "success" : "default"} />
                  </Stack>
                  <Typography variant="h2">{job.title || "Untitled role"}</Typography>
                  <Typography color="text.secondary" sx={{ mt: 0.5 }}>
                    {job.company_name || "Unknown company"}
                    {job.location ? ` · ${job.location}` : ""} · {job.source_host}
                    {job.updated_at ? ` · ${job.updated_at.slice(0, 10)}` : ""}
                  </Typography>
                  {job.required_skill_list.length > 0 && (
                    <Stack direction="row" gap={0.5} flexWrap="wrap" sx={{ mt: 1.2 }}>
                      {job.required_skill_list.slice(0, 6).map((skill) => (
                        <Chip key={skill} label={skill} />
                      ))}
                    </Stack>
                  )}
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
      {!jobs.length && (
        <Typography color="text.secondary">No positions yet. Add a job description above.</Typography>
      )}
    </Stack>
  );
}
