import NextAuth from "next-auth";
import GoogleProvider from "next-auth/providers/google";

export const authConfig = {
  secret: process.env.NEXTAUTH_SECRET,
  trustHost: true,

  pages: {
    signIn: "/auth/signin",
    error: "/auth/error",
  },

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

  callbacks: {
    async redirect() {
      return process.env.NEXTAUTH_URL!;
    },
  },

  cookies: {
    sessionToken: {
      name: "__Host-next-auth.session-token",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: true,
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
        secure: true,
      },
    },
  },
};

// NEXTAUTH v5 — This is the correct way
export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);
