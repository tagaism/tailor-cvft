import { ComponentProps, FormEvent, useEffect, useRef, useState } from "react";
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
import type {
  Certification,
  Education,
  Experience,
  ExperienceProject,
  Profile,
  Project,
} from "../types";

const emptyContact = {
  full_name: "",
  email: "",
  phone: "",
  location: "",
  linkedin: "",
  github: "",
  website: "",
};

const emptyRoleProject = (): ExperienceProject => ({ summary: "", impact: "" });
const PROJECT_BULLET_SEP = " — ";

function projectBullet(item: ExperienceProject): string {
  return [item.summary, item.impact].map((part) => part.trim()).filter(Boolean).join(PROJECT_BULLET_SEP);
}

const emptyExperience = (): Experience => ({
  title: "",
  company: "",
  location: "",
  start: "",
  end: "",
  current: false,
  bullets: [],
  projects: [emptyRoleProject()],
});

function hydrateRoleProjects(role: Experience): ExperienceProject[] {
  const filled = (role.projects ?? []).filter((item) => item.summary.trim() || item.impact.trim());
  if (filled.length) return filled;
  return (role.bullets ?? [])
    .map((item) => item.trim())
    .filter(Boolean)
    .map((bullet) => {
      const at = bullet.indexOf(PROJECT_BULLET_SEP);
      if (at >= 0) {
        return { summary: bullet.slice(0, at).trim(), impact: bullet.slice(at + PROJECT_BULLET_SEP.length).trim() };
      }
      return { summary: bullet, impact: "" };
    });
}

function hydrateProfile(profile: Profile): Profile {
  return {
    ...profile,
    experience: profile.experience.map((role) => ({
      ...role,
      projects: hydrateRoleProjects(role),
    })),
  };
}

function cleanProfile(profile: Profile): Profile {
  return {
    ...profile,
    skills: profile.skills.map((item) => item.trim()).filter(Boolean),
    additional_skills: profile.additional_skills.map((item) => item.trim()).filter(Boolean),
    experience: profile.experience.map((role) => {
      const projects = (role.projects ?? [])
        .map((item) => ({ summary: item.summary.trim(), impact: item.impact.trim() }))
        .filter((item) => item.summary || item.impact);
      return { ...role, projects, bullets: projects.map(projectBullet) };
    }),
    projects: profile.projects.map((project) => ({
      ...project,
      bullets: project.bullets.map((item) => item.trim()).filter(Boolean),
    })),
  };
}

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

function AutoSaveField({
  onSave,
  ...props
}: ComponentProps<typeof TextField> & { onSave: () => void }) {
  return (
    <TextField
      {...props}
      onBlur={(event) => {
        props.onBlur?.(event);
        onSave();
      }}
    />
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [error, setError] = useState("");
  const [flash, setFlash] = useState("");
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const profileRef = useRef<Profile | null>(null);
  const savingRef = useRef(false);
  const queuedRef = useRef(false);
  const lastSavedRef = useRef("");
  const uploadingRef = useRef(false);

  function commitProfile(next: Profile) {
    profileRef.current = next;
    setProfile(next);
  }

  async function saveNow(source: "blur" | "button" = "blur") {
    const snapshot = profileRef.current;
    if (!snapshot || uploadingRef.current) return;
    const cleaned = cleanProfile(snapshot);
    const payload = JSON.stringify(cleaned);
    if (source === "blur" && payload === lastSavedRef.current) return;
    if (savingRef.current) {
      queuedRef.current = true;
      return;
    }
    savingRef.current = true;
    if (source === "button") setSaving(true);
    setError("");
    try {
      const saved = await api.saveProfile(cleaned);
      lastSavedRef.current = JSON.stringify(cleanProfile(hydrateProfile(saved.profile)));
      if (source === "button") {
        commitProfile(hydrateProfile(saved.profile));
        setFlash("Profile saved.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save profile.");
    } finally {
      savingRef.current = false;
      setSaving(false);
      if (queuedRef.current) {
        queuedRef.current = false;
        void saveNow(source);
      }
    }
  }

  useEffect(() => {
    api
      .profile()
      .then((data) => {
        const next = hydrateProfile(data.profile);
        commitProfile(next);
        lastSavedRef.current = JSON.stringify(cleanProfile(next));
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  async function onSave(event: FormEvent) {
    event.preventDefault();
    await saveNow("button");
  }

  async function onUpload(event: FormEvent) {
    event.preventDefault();
    if (!file) {
      setError("Choose a CV file first, then click Extract and merge.");
      return;
    }
    uploadingRef.current = true;
    setUploading(true);
    setError("");
    try {
      const data = await api.uploadProfile(file);
      const next = hydrateProfile(data.profile);
      commitProfile(next);
      lastSavedRef.current = JSON.stringify(cleanProfile(next));
      setFlash("CV imported and merged into your profile. Review the fields below.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed.");
    } finally {
      uploadingRef.current = false;
      setUploading(false);
    }
  }

  if (!profile && !error) return <Typography color="text.secondary">Loading profile…</Typography>;
  if (!profile) return <Alert severity="error">{error}</Alert>;

  const saveOnBlur = () => void saveNow("blur");

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

      <Paper
        component="form"
        onSubmit={onSave}
        onBlur={(event) => {
          const next = event.relatedTarget as Node | null;
          if (next && event.currentTarget.contains(next)) return;
          void saveNow("blur");
        }}
        sx={{ p: 2.5 }}
      >
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
              <AutoSaveField onSave={saveOnBlur}
                label={label}
                value={profile.contact[key] || emptyContact[key]}
                onChange={(e) =>
                  commitProfile({ ...profile, contact: { ...profile.contact, [key]: e.target.value } })
                }
              />
            </Grid>
          ))}
          <Grid size={12}>
            <AutoSaveField onSave={saveOnBlur}
              label="Summary"
              multiline
              minRows={3}
              value={profile.summary}
              onChange={(e) => commitProfile({ ...profile, summary: e.target.value })}
            />
          </Grid>
          <Grid size={12}>
            <AutoSaveField onSave={saveOnBlur}
              label="Skills (one per line)"
              multiline
              minRows={4}
              value={profile.skills.join("\n")}
              onChange={(e) =>
                commitProfile({
                  ...profile,
                  skills: e.target.value.split("\n").map((line) => line.trimEnd()),
                })
              }
            />
          </Grid>
        </Grid>

        <RepeatHead
          title="Experience"
          onAdd={() => {
            commitProfile({ ...profile, experience: [...profile.experience, emptyExperience()] });
            void saveNow("blur");
          }}
        />
        {profile.experience.map((role, index) => (
          <Paper key={index} sx={{ p: 2, mb: 1.5 }}>
            <Stack direction="row" justifyContent="flex-end">
              <IconButton
                aria-label="Remove role"
                onClick={() => {
                  commitProfile({ ...profile, experience: profile.experience.filter((_, i) => i !== index) });
                  void saveNow("blur");
                }}
              >
                <DeleteOutline />
              </IconButton>
            </Stack>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Title"
                  value={role.title}
                  onChange={(e) => updateList(profile, commitProfile, "experience", index, { title: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Company"
                  value={role.company}
                  onChange={(e) => updateList(profile, commitProfile, "experience", index, { company: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Location"
                  value={role.location}
                  onChange={(e) => updateList(profile, commitProfile, "experience", index, { location: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Start"
                  value={role.start}
                  onChange={(e) => updateList(profile, commitProfile, "experience", index, { start: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 4 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="End"
                  value={role.end}
                  onChange={(e) => updateList(profile, commitProfile, "experience", index, { end: e.target.value })}
                />
              </Grid>
              <Grid size={12}>
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  alignItems="flex-start"
                  gap={1}
                  sx={{ mb: 1 }}
                >
                  <div>
                    <Typography variant="subtitle2" sx={{ fontWeight: 650 }}>
                      Projects
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      Summary of the work and its impact at this company.
                    </Typography>
                  </div>
                  <Button
                    type="button"
                    size="small"
                    sx={{ whiteSpace: "nowrap", flexShrink: 0 }}
                    onClick={() => {
                      updateList(profile, commitProfile, "experience", index, {
                        projects: [...(role.projects ?? []), emptyRoleProject()],
                      });
                    }}
                  >
                    + Add project
                  </Button>
                </Stack>
                {(role.projects ?? []).length === 0 ? (
                  <Typography color="text.secondary" variant="body2">
                    No projects yet. Add a summary and impact for this company.
                  </Typography>
                ) : (
                  (role.projects ?? []).map((project, projectIndex) => (
                    <Paper key={projectIndex} variant="outlined" sx={{ p: 1.5, mb: 1.5 }}>
                      <Stack direction="row" justifyContent="flex-end">
                        <IconButton
                          aria-label="Remove project"
                          onClick={() => {
                            updateList(profile, commitProfile, "experience", index, {
                              projects: (role.projects ?? []).filter((_, i) => i !== projectIndex),
                            });
                            void saveNow("blur");
                          }}
                        >
                          <DeleteOutline />
                        </IconButton>
                      </Stack>
                      <Grid container spacing={2}>
                        <Grid size={12}>
                          <AutoSaveField onSave={saveOnBlur}
                            label="Summary"
                            multiline
                            minRows={2}
                            value={project.summary}
                            onChange={(e) =>
                              patchRoleProject(profile, commitProfile, index, projectIndex, {
                                summary: e.target.value,
                              })
                            }
                          />
                        </Grid>
                        <Grid size={12}>
                          <AutoSaveField onSave={saveOnBlur}
                            label="Impact"
                            multiline
                            minRows={2}
                            helperText="Outcomes, metrics, or what changed"
                            value={project.impact}
                            onChange={(e) =>
                              patchRoleProject(profile, commitProfile, index, projectIndex, {
                                impact: e.target.value,
                              })
                            }
                          />
                        </Grid>
                      </Grid>
                    </Paper>
                  ))
                )}
              </Grid>
            </Grid>
          </Paper>
        ))}

        <RepeatHead
          title="Education"
          onAdd={() => {
            commitProfile({ ...profile, education: [...profile.education, emptyEducation()] });
            void saveNow("blur");
          }}
        />
        {profile.education.map((edu, index) => (
          <Paper key={index} sx={{ p: 2, mb: 1.5 }}>
            <Stack direction="row" justifyContent="flex-end">
              <IconButton
                aria-label="Remove school"
                onClick={() => {
                  commitProfile({ ...profile, education: profile.education.filter((_, i) => i !== index) });
                  void saveNow("blur");
                }}
              >
                <DeleteOutline />
              </IconButton>
            </Stack>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="School"
                  value={edu.school}
                  onChange={(e) => updateList(profile, commitProfile, "education", index, { school: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Degree"
                  value={edu.degree}
                  onChange={(e) => updateList(profile, commitProfile, "education", index, { degree: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Field"
                  value={edu.field}
                  onChange={(e) => updateList(profile, commitProfile, "education", index, { field: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Start"
                  value={edu.start}
                  onChange={(e) => updateList(profile, commitProfile, "education", index, { start: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="End"
                  value={edu.end}
                  onChange={(e) => updateList(profile, commitProfile, "education", index, { end: e.target.value })}
                />
              </Grid>
              <Grid size={12}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Details"
                  value={edu.details}
                  onChange={(e) => updateList(profile, commitProfile, "education", index, { details: e.target.value })}
                />
              </Grid>
            </Grid>
          </Paper>
        ))}

        <RepeatHead
          title="Projects"
          onAdd={() => {
            commitProfile({ ...profile, projects: [...profile.projects, emptyProject()] });
            void saveNow("blur");
          }}
        />
        {profile.projects.map((project, index) => (
          <Paper key={index} sx={{ p: 2, mb: 1.5 }}>
            <Stack direction="row" justifyContent="flex-end">
              <IconButton
                aria-label="Remove project"
                onClick={() => {
                  commitProfile({ ...profile, projects: profile.projects.filter((_, i) => i !== index) });
                  void saveNow("blur");
                }}
              >
                <DeleteOutline />
              </IconButton>
            </Stack>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Name"
                  value={project.name}
                  onChange={(e) => updateList(profile, commitProfile, "projects", index, { name: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="URL"
                  value={project.url}
                  onChange={(e) => updateList(profile, commitProfile, "projects", index, { url: e.target.value })}
                />
              </Grid>
              <Grid size={12}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Description"
                  value={project.description}
                  onChange={(e) =>
                    updateList(profile, commitProfile, "projects", index, { description: e.target.value })
                  }
                />
              </Grid>
              <Grid size={12}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Bullets (one per line)"
                  multiline
                  minRows={2}
                  value={project.bullets.join("\n")}
                  onChange={(e) =>
                    updateList(profile, commitProfile, "projects", index, { bullets: e.target.value.split("\n") })
                  }
                />
              </Grid>
            </Grid>
          </Paper>
        ))}

        <RepeatHead
          title="Certifications"
          onAdd={() => {
            commitProfile({ ...profile, certifications: [...profile.certifications, emptyCert()] });
            void saveNow("blur");
          }}
        />
        {profile.certifications.map((cert, index) => (
          <Paper key={index} sx={{ p: 2, mb: 1.5 }}>
            <Stack direction="row" justifyContent="flex-end">
              <IconButton
                aria-label="Remove certification"
                onClick={() => {
                  commitProfile({
                    ...profile,
                    certifications: profile.certifications.filter((_, i) => i !== index),
                  });
                  void saveNow("blur");
                }}
              >
                <DeleteOutline />
              </IconButton>
            </Stack>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 6 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Name"
                  value={cert.name}
                  onChange={(e) => updateList(profile, commitProfile, "certifications", index, { name: e.target.value })}
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Issuer"
                  value={cert.issuer}
                  onChange={(e) =>
                    updateList(profile, commitProfile, "certifications", index, { issuer: e.target.value })
                  }
                />
              </Grid>
              <Grid size={{ xs: 12, md: 3 }}>
                <AutoSaveField onSave={saveOnBlur}
                  label="Year"
                  value={cert.year}
                  onChange={(e) => updateList(profile, commitProfile, "certifications", index, { year: e.target.value })}
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
      <Button type="button" onClick={onAdd}>
        + Add
      </Button>
    </Stack>
  );
}

function patchRoleProject(
  profile: Profile,
  setProfile: (profile: Profile) => void,
  roleIndex: number,
  projectIndex: number,
  patch: Partial<ExperienceProject>,
) {
  const role = profile.experience[roleIndex];
  const projects = (role.projects ?? []).map((item, i) =>
    i === projectIndex ? { ...item, ...patch } : item,
  );
  updateList(profile, setProfile, "experience", roleIndex, { projects });
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
