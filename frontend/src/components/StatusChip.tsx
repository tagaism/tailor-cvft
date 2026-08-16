import Chip from "@mui/material/Chip";
import { useTheme } from "@mui/material/styles";
import type { ApplicationStatus } from "../types";

export default function StatusChip({ status, label }: { status: ApplicationStatus; label: string }) {
  const theme = useTheme();
  const color = theme.palette.status[status] ?? theme.palette.text.secondary;
  return <Chip label={label} sx={{ bgcolor: `${color}18`, color, borderColor: color }} variant="outlined" />;
}
