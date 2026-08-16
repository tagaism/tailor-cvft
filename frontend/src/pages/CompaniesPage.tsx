import { FormEvent, useEffect, useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActionArea from "@mui/material/CardActionArea";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid2";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import type { Company } from "../types";

export default function CompaniesPage() {
  const navigate = useNavigate();
  const [companies, setCompanies] = useState<Company[]>([]);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", website: "", location: "" });
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api
      .companies()
      .then((data) => setCompanies(data.companies))
      .catch((err: Error) => setError(err.message));
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    setError("");
    try {
      const company = await api.createCompany(form);
      navigate(`/companies/${company.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save company.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Stack spacing={3}>
      <div>
        <Typography variant="h1">Companies</Typography>
        <Typography color="text.secondary">
          Employers you are tracking. Positions stay linked when you change the company name.
        </Typography>
      </div>
      {error && <Alert severity="error">{error}</Alert>}
      <Paper component="form" onSubmit={onCreate} sx={{ p: 2.5 }}>
        <Typography variant="h2" sx={{ mb: 2 }}>
          Add company
        </Typography>
        <Grid container spacing={2}>
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              required
              label="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              label="Website"
              type="url"
              value={form.website}
              onChange={(e) => setForm({ ...form, website: e.target.value })}
            />
          </Grid>
          <Grid size={{ xs: 12, md: 4 }}>
            <TextField
              label="Location"
              value={form.location}
              onChange={(e) => setForm({ ...form, location: e.target.value })}
            />
          </Grid>
        </Grid>
        <Button type="submit" variant="contained" sx={{ mt: 2 }} disabled={saving}>
          {saving ? "Saving…" : "Save company"}
        </Button>
      </Paper>
      <Grid container spacing={2}>
        {companies.map((company) => (
          <Grid key={company.id} size={{ xs: 12, md: 6 }}>
            <Card>
              <CardActionArea component={RouterLink} to={`/companies/${company.id}`}>
                <CardContent>
                  <Typography variant="h2">{company.name}</Typography>
                  <Typography color="text.secondary">
                    {company.position_count} position{company.position_count === 1 ? "" : "s"}
                    {company.location ? ` · ${company.location}` : ""}
                  </Typography>
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Stack>
  );
}
