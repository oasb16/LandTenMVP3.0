import NextAuth from "next-auth";
import Google from "next-auth/providers/google";

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
    async redirect({ url, baseUrl }) {
      // Stay in-domain and avoid loops
      if (url.startsWith("/")) return url;
      if (new URL(url).origin === baseUrl) return url;
      return baseUrl;
    },
  },

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

export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);
