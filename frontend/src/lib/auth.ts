import NextAuth, { type NextAuthConfig } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

export const authConfig: NextAuthConfig = {
  secret: process.env.NEXTAUTH_SECRET,

  // IMPORTANT: force NextAuth to trust Vercel domain
  trustHost: true,

  // Critical for preventing CSRF issues in production
  pages: {
    signIn: "/auth/signin",
    error: "/auth/error",
  },

  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code",
        },
      },
    }),
  ],

  callbacks: {
    // Ensure redirects ALWAYS stay on your deployed domain
    async redirect({ url, baseUrl }) {
      // Always force callback URLs to use the host from NEXTAUTH_URL
      return `${process.env.NEXTAUTH_URL}`;
    },
  },

  // Fix Vercel production cookies
  cookies: {
    sessionToken: {
      name: "__Host-next-auth.session-token",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: true,                // REQUIRED on Vercel
      },
    },
    callbackUrl: {
      name: "__Host-next-auth.callback-url",
      options: {
        sameSite: "lax",
        path: "/",
        secure: true,
      },
    },
    csrfToken: {
      name: "__Host-next-auth.csrf-token",
      options: {
        httpOnly: false,
        sameSite: "lax",
        path: "/",
        secure: true,        // REQUIRED — this is your fix
      },
    },
  },

  logger: {
    error(error) {
      console.error("[nextauth-error]", error);
    },
  },
};

// Export NextAuth handlers
export const { handlers: { GET, POST } } = NextAuth(authConfig);
