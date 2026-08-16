import { FormEvent, useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Grid from "@mui/material/Grid2";
import IconButton from "@mui/material/IconButton";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import DeleteOutline from "@mui/icons-material/DeleteOutline";
import { api } from "../api";
import type { Certification, Education, Experience, Profile, Project } from "../types";

const emptyContact = {
  full_name: "",
  email: "",
  phone: "",
  location: "",
  linkedin: "",
  github: "",
  website: "",
};

const emptyExperience = (): Experience => ({
  title: "",
  company: "",
  location: "",
  start: "",
  end: "",
  current: false,
  bullets: [],
});

const emptyEducation = (): Education => ({
  school: "",
  degree: "",
  field: "",
  start: "",
  end: "",
  location: "",
  details: "",
});

const emptyProject = (): Project => ({ name: "", url: "", description: "", bullets: [] });
const emptyCert = (): Certification => ({ name: "", issuer: "", year: "" });

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);

  useEffect(() => {
    api
      .profile()
      .then((data) => setProfile(data.profile))
      .catch((err: Error) => setError(err.message));
  }, []);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    if (!profile) return;
    setSaving(true);
    setError("");
    try {
      const cleaned: Profile = {
        ...profile,
        skills: profile.skills.map((item) => item.trim()).filter(Boolean),
        additional_skills: profile.additional_skills.map((item) => item.trim()).filter(Boolean),
        experience: profile.experience.map((role) => ({
          ...role,
          bullets: role.bullets.map((item) => item.trim()).filter(Boolean),
        })),
        projects: profile.projects.map((project) => ({
          ...project,
          bullets: project.bullets.map((item) => item.trim()).filter(Boolean),
        })),
      };
      const saved = await api.saveProfile(cleaned);
      setProfile(saved.profile);
      setFlash("Profile saved.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile.");
    } finally {
      setSaving(false);
    }
  }

  async function onUpload(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("Choose a CV file first, then click Extract and merge.");
      return;
    }
    setUploading(true);
    setError("");
    try {
      const data = await api.uploadProfile(file);
      setProfile(data.profile);
      setFlash("CV imported and merged into your profile. Review the fields below.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  if (!profile && !error) return <Typography color="text.secondary">Loading profile…</Typography>;
  if (!profile) return <Alert severity="error">{error}</Alert>;

  return (
    <Stack spacing={3}>
      <div>
        <Typography variant="h1">Your profile</Typography>
        <Typography color="text.secondary">This is the source of truth. Tailored CVs may only rephrase what is here.</Typography>
      </div>
      {flash && <Alert severity="success">{flash}</Alert>}
      {error && <Alert severity="error">{error}</Alert>}

      <Paper component="form" onSubmit={onUpload} sx={{ p: 2.5 }}>
        <Typography variant="h2" sx={{ mb: 1 }}>
          Upload a CV to seed this profile
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} gap={2} alignItems="center">
          <Button variant="outlined" component="label">
            Choose PDF, DOCX, or TXT
            <input
              hidden
              type="file"
              accept=".pdf,.docx,.txt,.md,application/pdf"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            />
          </Button>
          <Typography color="text.secondary">{file ? `Selected: ${file.name}` : "No file chosen"}</Typography>
          <Button type="submit" variant="contained" disabled={uploading}>
            {uploading ? "Extracting…" : "Extract and merge"}
          </Button>
        </Stack>
      </Paper>

      <Paper component="form" onSubmit={onSave} sx={{ p: 2.5 }}>
        <Typography variant="h2" sx={{ mb: 2 }}>
          Contact
        </Typography>
        <Grid container spacing={2}>
          {(
            [
              ["full_name", "Full name"],
              ["email", "Email"],
              ["phone", "Phone"],
              ["location", "Location"],
              ["linkedin", "LinkedIn"],
              ["github", "GitHub"],
              ["website", "Website"],
            ] as const
          ).map(([key, label]) => (
            <Grid key={key} size={{ xs: 12, md: key === "website" ? 12 : 6 }}>
              <TextField
                label={label}
                value={profile.contact[key] || emptyContact[key]}
                onChange={(e) =>
                  setProfile({ ...profile, contact: { ...profile.contact, [key]: e.target.value } })
                }
              />
            </Grid>
          ))}
          <Grid size={12}>
            <TextField
              label="Summary"
              multiline
              minRows={3}
              value={profile.summary}
              onChange={(e) => setProfile({ ...profile, summary: e.target.value })}
            />
          </Grid>
          <Grid size={12}>
            <TextField
              label="Skills (one per line)"
              multiline
              minRows={4}
              value={profile.skills.join("\n")}
              onChange={(e) =>
                setProfile({
                  ...profile,
                  skills: e.target.value.split("\n").map((line) => line.trimEnd()),
                })
              }
            />
          </Grid>
        </Grid>

        <RepeatHead
          title="Experience"
          onAdd={() => setProfile({ ...profile, experience: [...profile.experience, emptyExperience()] })}
        />
        {profile.experience.map((role, index) => (
          <Paper key={index} sx={{ p: 2, mb: 1.5 }}>
            <Stack direction="row" justifyContent="flex-end">
              <IconButton
                aria-label="Remove role"
                onClick={() =>
                  setProfile({ ...profile, experience: profile.experience.filter((_, i) => i !== index) })
                }
              >
                <DeleteOutline />
              </IconButton>
            </Stack>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="Title"
                  value={role.title}
                  onChange={(e) => updateList(profile, setProfile, "experience", index, { title: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="Company"
                  value={role.company}
                  onChange={(e) => updateList(profile, setProfile, "experience", index, { company: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField
                  label="Location"
                  value={role.location}
                  onChange={(e) => updateList(profile, setProfile, "experience", index, { location: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField
                  label="Start"
                  value={role.start}
                  onChange={(e) => updateList(profile, setProfile, "experience", index, { start: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <TextField
                  label="End"
                  value={role.end}
                  onChange={(e) => updateList(profile, setProfile, "experience", index, { end: e.target.value })}
                />
              </Grid>
              <Grid size={12}>
                <TextField
                  label="Bullets (one per line)"
                  multiline
                  minRows={3}
                  value={role.bullets.join("\n")}
                  onChange={(e) =>
                    updateList(profile, setProfile, "experience", index, {
                      bullets: e.target.value.split("\n"),
                    })
                  }
                />
              </Grid>
            </Grid>
          </Paper>
        ))}

        <RepeatHead
          title="Education"
          onAdd={() => setProfile({ ...profile, education: [...profile.education, emptyEducation()] })}
        />
        {profile.education.map((edu, index) => (
          <Paper key={index} sx={{ p: 2, mb: 1.5 }}>
            <Stack direction="row" justifyContent="flex-end">
              <IconButton
                aria-label="Remove school"
                onClick={() =>
                  setProfile({ ...profile, education: profile.education.filter((_, i) => i !== index) })
                }
              >
                <DeleteOutline />
              </IconButton>
            </Stack>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="School"
                  value={edu.school}
                  onChange={(e) => updateList(profile, setProfile, "education", index, { school: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="Degree"
                  value={edu.degree}
                  onChange={(e) => updateList(profile, setProfile, "education", index, { degree: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="Field"
                  value={edu.field}
                  onChange={(e) => updateList(profile, setProfile, "education", index, { field: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <TextField
                  label="Start"
                  value={edu.start}
                  onChange={(e) => updateList(profile, setProfile, "education", index, { start: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <TextField
                  label="End"
                  value={edu.end}
                  onChange={(e) => updateList(profile, setProfile, "education", index, { end: e.target.value })}
                />
              </Grid>
              <Grid size={12}>
                <TextField
                  label="Details"
                  value={edu.details}
                  onChange={(e) => updateList(profile, setProfile, "education", index, { details: e.target.value })}
                />
              </Grid>
            </Grid>
          </Paper>
        ))}

        <RepeatHead
          title="Projects"
          onAdd={() => setProfile({ ...profile, projects: [...profile.projects, emptyProject()] })}
        />
        {profile.projects.map((project, index) => (
          <Paper key={index} sx={{ p: 2, mb: 1.5 }}>
            <Stack direction="row" justifyContent="flex-end">
              <IconButton
                aria-label="Remove project"
                onClick={() => setProfile({ ...profile, projects: profile.projects.filter((_, i) => i !== index) })}
              >
                <DeleteOutline />
              </IconButton>
            </Stack>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="Name"
                  value={project.name}
                  onChange={(e) => updateList(profile, setProfile, "projects", index, { name: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="URL"
                  value={project.url}
                  onChange={(e) => updateList(profile, setProfile, "projects", index, { url: e.target.value })}
                />
              </Grid>
              <Grid size={12}>
                <TextField
                  label="Description"
                  value={project.description}
                  onChange={(e) =>
                    updateList(profile, setProfile, "projects", index, { description: e.target.value })
                  }
                />
              </Grid>
              <Grid size={12}>
                <TextField
                  label="Bullets (one per line)"
                  multiline
                  minRows={2}
                  value={project.bullets.join("\n")}
                  onChange={(e) =>
                    updateList(profile, setProfile, "projects", index, { bullets: e.target.value.split("\n") })
                  }
                />
              </Grid>
            </Grid>
          </Paper>
        ))}

        <RepeatHead
          title="Certifications"
          onAdd={() => setProfile({ ...profile, certifications: [...profile.certifications, emptyCert()] })}
        />
        {profile.certifications.map((cert, index) => (
          <Paper key={index} sx={{ p: 2, mb: 1.5 }}>
            <Stack direction="row" justifyContent="flex-end">
              <IconButton
                aria-label="Remove certification"
                onClick={() =>
                  setProfile({
                    ...profile,
                    certifications: profile.certifications.filter((_, i) => i !== index),
                  })
                }
              >
                <DeleteOutline />
              </IconButton>
            </Stack>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <TextField
                  label="Name"
                  value={cert.name}
                  onChange={(e) => updateList(profile, setProfile, "certifications", index, { name: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <TextField
                  label="Issuer"
                  value={cert.issuer}
                  onChange={(e) =>
                    updateList(profile, setProfile, "certifications", index, { issuer: e.target.value })
                  }
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <TextField
                  label="Year"
                  value={cert.year}
                  onChange={(e) => updateList(profile, setProfile, "certifications", index, { year: e.target.value })}
                />
              </Grid>
            </Grid>
          </Paper>
        ))}

        <Button type="submit" variant="contained" sx={{ mt: 1 }} disabled={saving}>
          {saving ? "Saving…" : "Save profile"}
        </Button>
      </Paper>
    </Stack>
  );
}

function RepeatHead({ title, onAdd }: { title: string; onAdd: () => void }) {
  return (
    <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mt: 3, mb: 1 }}>
      <Typography variant="h2">{title}</Typography>
      <Button onClick={onAdd}>+ Add</Button>
    </Stack>
  );
}

function updateList<K extends "experience" | "education" | "projects" | "certifications">(
  profile: Profile,
  setProfile: (profile: Profile) => void,
  key: K,
  index: number,
  patch: Partial<Profile[K][number]>,
) {
  const next = profile[key].map((item, i) => (i === index ? { ...item, ...patch } : item));
  setProfile({ ...profile, [key]: next });
}
