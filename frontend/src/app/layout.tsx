import "./globals.css";
import ClientProviders from "@/components/ClientProviders";

export const metadata = {
  title: "LandTenMVP3",
  description: "Modern landlord–tenant operations platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}

