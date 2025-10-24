import NextAuth, { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";

const backendBase = process.env.BACKEND_URL || process.env.NEXT_PUBLIC_BACKEND_URL || "";

const authSecret = process.env.NEXTAUTH_SECRET || process.env.AUTH_SECRET || "dev-secret";

const authConfig: NextAuthOptions = {
  secret: authSecret,
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? "",
    }),
  ],
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
