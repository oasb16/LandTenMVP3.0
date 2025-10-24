import { DefaultSession } from "next-auth";

declare module "next-auth" {
  interface Session {
    user: {
      id?: string | null;
      persona?: string | null;
    } & DefaultSession["user"];
  }

  interface User {
    persona?: string | null;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    persona?: string | null;
  }
}
