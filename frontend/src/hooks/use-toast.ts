type ToastArgs = {
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
};

export function useToast() {
  const toast = ({ title, description, variant }: ToastArgs) => {
    if (typeof window !== "undefined") {
      const message = [title, description].filter(Boolean).join(" - ");
      if (variant === "destructive") {
        console.error(message || "Toast");
      } else {
        console.log(message || "Toast");
      }
    }
  };

  return { toast };
}

export default useToast;
