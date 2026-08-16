import { useEffect, useState } from "react";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import Tab from "@mui/material/Tab";
import Tabs from "@mui/material/Tabs";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import { api } from "../api";
import type { LlmHealth } from "../types";

const tabs = [
  { to: "/jobs", label: "Positions" },
  { to: "/companies", label: "Companies" },
  { to: "/profile", label: "Profile" },
];

export default function AppShell() {
  const location = useLocation();
  const current = tabs.find((tab) => location.pathname.startsWith(tab.to))?.to ?? "/jobs";
  const [llm, setLlm] = useState<LlmHealth | null>(null);

  useEffect(() => {
    api
      .health()
      .then((data) => setLlm(data.llm))
      .catch(() => setLlm({ ok: false, model: "", message: "API unreachable" }));
  }, []);

  return (
    <Box sx={{ minHeight: "100vh" }}>
      <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: 1, borderColor: "divider" }}>
        <Toolbar sx={{ gap: 2 }}>
          <Typography
            component={RouterLink}
            to="/jobs"
            variant="h6"
            sx={{ color: "text.primary", textDecoration: "none", fontWeight: 750, mr: 1 }}
          >
            tailor
            <Box component="span" sx={{ color: "primary.main" }}>
              -cvft
            </Box>
          </Typography>
          <Tabs value={current} sx={{ minHeight: 48, flex: 1 }}>
            {tabs.map((tab) => (
              <Tab
                key={tab.to}
                value={tab.to}
                label={tab.label}
                component={RouterLink}
                to={tab.to}
                sx={{ minHeight: 48 }}
              />
            ))}
          </Tabs>
          {llm && (
            <Chip
              size="small"
              color={llm.ok ? "success" : "error"}
              variant="outlined"
              label={llm.message}
              title={llm.message}
            />
          )}
        </Toolbar>
      </AppBar>
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Outlet />
      </Container>
    </Box>
  );
}
