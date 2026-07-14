const AUTH_ENDPOINTS = {
  login: "auth/login/",
  register: "auth/register/",
  logout: "auth/logout/",
} as const;

fetch(`/api/${AUTH_ENDPOINTS.login}`);
fetch(`/api/${AUTH_ENDPOINTS.register}`);
fetch(`/api/${AUTH_ENDPOINTS.logout}`);
