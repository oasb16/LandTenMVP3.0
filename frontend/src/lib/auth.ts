import NextAuth, { type NextAuthConfig } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

const backendBase = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "";

const authSecret = process.env.NEXTAUTH_SECRET || process.env.AUTH_SECRET || "dev-secret";

const authConfig: NextAuthConfig = {
  secret: authSecret,
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code",
        },
      },
    }),
  ],
  // Trust host and global error redirect safeguard
  trustHost: true,
  pages: {
    error: "/auth/error",
  },
  // Provide a logger to capture NextAuth internal errors in a typed way
  logger: {
    error: (error: Error) => {
      try {
        console.error("[auth][critical-error]", error?.message || error, error);
      } catch (e) {
        // swallow
      }
    },
    warn: (message: string) => {
      try {
        console.warn("[auth][warn]", message);
      } catch (e) {
        // swallow
      }
    },
    debug: (message: string) => {
      if (process.env.NODE_ENV !== "production") {
        try {
          console.debug("[auth][debug]", message);
        } catch (e) {
          // swallow
        }
      }
    },
  },
  cookies: {
    pkceCodeVerifier: {
      name: "next-auth.pkce.code_verifier",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: process.env.NODE_ENV === "production",
      },
    },
  },
  debug: process.env.NODE_ENV !== "production",
  callbacks: {
    async jwt({ token, trigger, session, account, profile }) {
      if (account?.provider === "google" && profile?.email) {
        token.email = profile.email;
      }
      if (trigger === "update" && session?.persona) {
        token.persona = session.persona;
      }
      if (!token.persona && token.email && backendBase) {
        try {
          const res = await fetch(`${backendBase}/profile/${encodeURIComponent(token.email)}`);
          if (res.ok) {
            const data = await res.json();
            token.persona = data?.persona || null;
          }
        } catch {
          // ignore
        }
      }
      return token;
    },
    async session({ session, token }) {
      if (token.email) {
        session.user.email = token.email as string;
        session.user.id = token.email as string;
      }
      session.user.persona = (token.persona as string | undefined) || null;
      return session;
    },
  },
};

export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);

export const authOptions = authConfig;
