import { FormEvent, useEffect, useState } from "react";
import { Link as RouterLink, useNavigate, useParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import Grid from "@mui/material/Grid2";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import StatusChip from "../components/StatusChip";
import { parseRouteId } from "../ids";
import type { Company } from "../types";

export default function CompanyDetailPage() {
  const { id } = useParams();
  const companyId = parseRouteId(id);
  const navigate = useNavigate();
  const [company, setCompany] = useState<Company | null>(null);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [saving, setSaving] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  useEffect(() => {
    if (companyId == null) return;
    let cancelled = false;
    setError("");
    setCompany(null);
    api
      .company(companyId)
      .then((data) => {
        if (!cancelled) setCompany(data);
      })
      .catch((err: Error) => {
        if (!cancelled) setError(err.message || "Company not found.");
      });
    return () => {
      cancelled = true;
    };
  }, [companyId]);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!company) return;
    setSaving(true);
    setError("");
    try {
      setCompany(
        await api.saveCompany(company.id, {
          name: company.name,
          website: company.website,
          location: company.location,
          notes: company.notes,
        }),
      );
      setFlash("Company saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save.");
    } finally {
      setSaving(false);
    }
  }

  async function onDelete() {
    if (!company) return;
    try {
      await api.deleteCompany(company.id);
      navigate("/companies");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete.");
      setConfirmDelete(false);
    }
  }

  if (companyId == null) {
    return (
      <Alert severity="error">
        Company not found. <RouterLink to="/companies">Back to companies</RouterLink>
      </Alert>
    );
  }
  if (!company && error) {
    return (
      <Alert severity="error">
        {error} <RouterLink to="/companies">Back to companies</RouterLink>
      </Alert>
    );
  }
  if (!company) return <Typography color="text.secondary">Loading…</Typography>;

  return (
    <Stack spacing={3}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
        <div>
          <Typography color="text.secondary">
            <RouterLink to="/companies">Companies</RouterLink>
          </Typography>
          <Typography variant="h1">{company.name}</Typography>
          <Typography color="text.secondary">
            {company.position_count} position{company.position_count === 1 ? "" : "s"}
            {company.location ? ` · ${company.location}` : ""}
          </Typography>
        </div>
        <Button color="error" variant="outlined" onClick={() => setConfirmDelete(true)}>
          Delete
        </Button>
      </Stack>
      {flash && <Alert severity="success">{flash}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}

      <Paper component="form" onSubmit={onSave} sx={{ p: 2.5 }}>
        <Typography variant="h2" sx={{ mb: 2 }}>
          Company
        </Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              required
              label="Name"
              value={company.name}
              onChange={(e) => setCompany({ ...company, name: e.target.value })}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 6 }}>
            <TextField
              label="Location"
              value={company.location}
              onChange={(e) => setCompany({ ...company, location: e.target.value })}
            />
          </Grid>
          <Grid size={12}>
            <TextField
              label="Website"
              type="url"
              value={company.website}
              onChange={(e) => setCompany({ ...company, website: e.target.value })}
            />
          </Grid>
          <Grid size={12}>
            <TextField
              label="Notes"
              multiline
              minRows={3}
              value={company.notes}
              onChange={(e) => setCompany({ ...company, notes: e.target.value })}
            />
          </Grid>
        </Grid>
        <Button type="submit" variant="outlined" sx={{ mt: 2 }} disabled={saving}>
          {saving ? "Saving…" : "Save company"}
        </Button>
      </Paper>

      <Paper sx={{ p: 2.5 }}>
        <Stack direction="row" justifyContent="space-between" sx={{ mb: 2 }}>
          <Typography variant="h2">Positions</Typography>
          <Button component={RouterLink} to="/jobs" variant="outlined">
            Add position
          </Button>
        </Stack>
        <Grid container spacing={2}>
          {(company.positions || []).map((job) => (
            <Grid key={job.id} size={{ xs: 12, md: 6 }}>
              <Card>
                <CardActionArea component={RouterLink} to={`/jobs/${job.id}`}>
                  <CardContent>
                    <Stack direction="row" gap={1} sx={{ mb: 1 }}>
                      <StatusChip status={job.status} label={job.status_label} />
                      <Chip label={job.has_generation ? "CV ready" : "No CV"} color={job.has_generation ? "success" : "default"} />
                    </Stack>
                    <Typography variant="h2">{job.title || "Untitled role"}</Typography>
                  </CardContent>
                </CardActionArea>
              </Card>
            </Grid>
          ))}
        </Grid>
        {!company.positions?.length && <Typography color="text.secondary">No positions linked yet.</Typography>}
      </Paper>

      <Dialog open={confirmDelete} onClose={() => setConfirmDelete(false)}>
        <DialogTitle>Delete this company?</DialogTitle>
        <DialogContent>
          <DialogContentText>Positions must be removed first.</DialogContentText>
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
