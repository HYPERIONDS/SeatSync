import { Navigate, Route, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { useAuth } from "./hooks/useAuth";
import { AuthPage } from "./pages/AuthPage";
import { BookingsPage } from "./pages/BookingsPage";
import { DiscoverPage } from "./pages/DiscoverPage";
import { EventPage } from "./pages/EventPage";
import { OrganizerPage } from "./pages/OrganizerPage";
import type { Role } from "./types";

function Protected({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { user } = useAuth();
  return user && roles.includes(user.role) ? children : <Navigate to="/login" replace />;
}

export default function App() {
  return <Routes><Route element={<Layout />}><Route index element={<DiscoverPage />} /><Route path="events/:eventId" element={<EventPage />} /><Route path="login" element={<AuthPage />} /><Route path="bookings" element={<Protected roles={["CUSTOMER"]}><BookingsPage /></Protected>} /><Route path="organizer" element={<Protected roles={["ORGANIZER", "ADMIN"]}><OrganizerPage /></Protected>} /><Route path="*" element={<Navigate to="/" />} /></Route></Routes>;
}
