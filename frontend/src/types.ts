export type ApplicationStatus =
  | "saved"
  | "applied"
  | "under_consideration"
  | "rejected"
  | "declined";

export type StatusOption = {
  value: ApplicationStatus;
  label: string;
  hint: string;
};

export type LlmHealth = {
  ok: boolean;
  provider?: string;
  model: string;
  message: string;
  checked_at?: string;
};

export type Health = {
  ok: boolean;
  llm: LlmHealth;
  statuses: StatusOption[];
};

export type Contact = {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  linkedin: string;
  github: string;
  website: string;
};

export type Experience = {
  title: string;
  company: string;
  location: string;
  start: string;
  end: string;
  current: boolean;
  bullets: string[];
};

export type Education = {
  school: string;
  degree: string;
  field: string;
  start: string;
  end: string;
  location: string;
  details: string;
};

export type Project = {
  name: string;
  url: string;
  description: string;
  bullets: string[];
};

export type Certification = {
  name: string;
  issuer: string;
  year: string;
};

export type Profile = {
  contact: Contact;
  summary: string;
  skills: string[];
  additional_skills: string[];
  experience: Experience[];
  education: Education[];
  projects: Project[];
  certifications: Certification[];
};

export type KeywordCoverage = {
  keyword: string;
  present: boolean;
};

export type MatchAnalysis = {
  matched_skills: string[];
  missing_skills: string[];
  keyword_coverage: KeywordCoverage[];
  emphasis: string[];
  gaps: string[];
  talking_points: string[];
};

export type Generation = {
  id: number;
  created_at: string | null;
  model_name: string;
  cover_letter: string;
  cv: Profile;
  match: MatchAnalysis;
};

export type Job = {
  id: number;
  title: string;
  company: string;
  company_id: number | null;
  company_name: string;
  url: string;
  location: string;
  source_text: string;
  required_skills: string;
  desired_skills: string;
  required_skill_list: string[];
  desired_skill_list: string[];
  notes: string;
  scrape_warning: string;
  status: ApplicationStatus;
  status_label: string;
  status_note: string;
  applied_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  source_host: string;
  has_generation: boolean;
  generation?: Generation | null;
  profile_ready?: boolean;
};

export type Company = {
  id: number;
  name: string;
  website: string;
  location: string;
  notes: string;
  created_at: string | null;
  updated_at: string | null;
  position_count: number;
  positions?: Job[];
};
