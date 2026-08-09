import { ApiError } from "@/lib/api";

export function userFacingError(error: unknown, fallback = "Something went wrong.") {
  if (error instanceof ApiError) {
    if (error.status >= 500) {
      return "Server error. Check the backend/worker services, then retry.";
    }
    if (error.status === 404) {
      return "This item no longer exists. Refresh the page and try again.";
    }
    if (error.status === 401 || error.status === 403) {
      return "You are not allowed to perform this action.";
    }
    if (error.status === 400) {
      return error.message || "Invalid request. Please check your inputs and retry.";
    }
    return error.message || fallback;
  }

  if (error instanceof TypeError && /fetch|network/i.test(error.message)) {
    return "Unable to reach the API (http://localhost:8000). Ensure backend is running.";
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

