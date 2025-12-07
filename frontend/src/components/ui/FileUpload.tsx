import React from "react";

type FileUploadProps = {
  onFilesSelected?: (files: File[]) => void;
  accept?: string;
  multiple?: boolean;
  className?: string;
};

export function FileUpload({ onFilesSelected, accept, multiple = true, className }: FileUploadProps) {
  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files ? Array.from(e.target.files) : [];
    onFilesSelected?.(files);
  };

  return (
    <input
      type="file"
      accept={accept}
      multiple={multiple}
      className={className}
      onChange={handleChange}
    />
  );
}

export default FileUpload;
