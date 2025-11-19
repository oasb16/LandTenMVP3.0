import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

// Backend base URL
const BACKEND_BASE =
  process.env.BACKEND_INTERNAL_URL ||
  process.env.BACKEND_URL ||
  "http://localhost:8080"; // local dev fallback

export const authConfig = {
  secret: process.env.NEXTAUTH_SECRET,
  trustHost: true,

  pages: {
    signIn: "/auth/signin",
    error: "/auth/error",
  },

  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],

  callbacks: {
    /**
     * 🔵 SESSION CALLBACK
     * Expose persona to the browser
     */
    async session({ session, token }) {
      if (session.user) {
        session.user.persona = token.persona as string | undefined;
      }
      return session;
    },

    /**
     * 🔵 JWT CALLBACK
     * Runs on every login. Auto-creates profile on the backend.
     */
    async jwt({ token, user }) {
      // Only run on first login OR if token doesn’t have persona yet
      if (user?.email && !token.persona) {
        console.log("[auth] Persona sync starting…");

        const email = user.email;
        const name = user.name ?? "";

        const base = BACKEND_BASE.replace(/\/$/, "");

        try {
          // 1. Try to read existing profile
          const res = await fetch(`${base}/profile/${encodeURIComponent(email)}`);

          if (res.status === 404) {
            console.log("[auth] Persona missing — creating default…");

            // 2. Auto-create profile
            const createRes = await fetch(`${base}/profile`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                user_id: email,
                name,
                persona: "tenant",
              }),
            });

            if (!createRes.ok) {
              console.error("[auth] Failed to create profile:", await createRes.text());
            } else {
              const created = await createRes.json();
              token.persona = created.persona ?? "tenant";
              console.log("[auth] Persona created:", token.persona);
            }
          } else if (res.ok) {
            // 3. Existing profile
            const profile = await res.json();
            token.persona = profile.persona ?? "tenant";
            console.log("[auth] Persona loaded:", token.persona);
          } else {
            console.error("[auth] Persona GET failed:", await res.text());
          }
        } catch (err) {
          console.error("[auth] Persona sync error:", err);
        }
      }

      return token;
    },

    /**
     * 🔵 REDIRECT CALLBACK
     * Prevent infinite loops
     */
    async redirect({ url, baseUrl }) {
      if (url.startsWith("/")) return url;
      if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    },
  },

  /**
   * 🔵 COOKIE CONFIG
   * Required for Vercel domain + secure
   */
  cookies: {
    sessionToken: {
      name: "__Host-next-auth.session-token",
      options: {
        httpOnly: true,
        sameSite: "lax",
        secure: true,
        path: "/",
      },
    },
  },
};

// Export NextAuth helpers
export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);
