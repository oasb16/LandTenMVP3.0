'use client';

import { useState, useRef, ChangeEvent, DragEvent } from 'react';
import { Upload, X, Image as ImageIcon } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  maxFiles?: number;
  acceptedTypes?: string[];
  multiple?: boolean;
}

export function FileUpload({
  onFilesSelected,
  maxFiles = 10,
  acceptedTypes = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp'],
  multiple = true,
}: FileUploadProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFiles = (files: FileList | null) => {
    if (!files) return;

    const fileArray = Array.from(files);
    const validFiles = fileArray.filter((file) =>
      acceptedTypes.includes(file.type)
    );

    if (validFiles.length === 0) {
      alert('Please select valid image files (JPEG, PNG, WebP)');
      return;
    }

    const newFiles = multiple
      ? [...selectedFiles, ...validFiles].slice(0, maxFiles)
      : validFiles.slice(0, 1);

    setSelectedFiles(newFiles);
    onFilesSelected(newFiles);

    // Generate previews
    const newPreviews: string[] = [];
    newFiles.forEach((file) => {
      const reader = new FileReader();
      reader.onloadend = () => {
        newPreviews.push(reader.result as string);
        if (newPreviews.length === newFiles.length) {
          setPreviews(newPreviews);
        }
      };
      reader.readAsDataURL(file);
    });
  };

  const handleFileInput = (e: ChangeEvent<HTMLInputElement>) => {
    handleFiles(e.target.files);
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const removeFile = (index: number) => {
    const newFiles = selectedFiles.filter((_, i) => i !== index);
    const newPreviews = previews.filter((_, i) => i !== index);
    setSelectedFiles(newFiles);
    setPreviews(newPreviews);
    onFilesSelected(newFiles);
  };

  const openFileDialog = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="space-y-4">
      <Card
        className={`border-2 border-dashed p-8 text-center cursor-pointer transition-colors ${
          isDragging
            ? 'border-primary bg-primary/5'
            : 'border-muted-foreground/25 hover:border-primary/50'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={openFileDialog}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple={multiple}
          accept={acceptedTypes.join(',')}
          onChange={handleFileInput}
          className="hidden"
        />
        <Upload className="h-12 w-12 mx-auto mb-4 text-muted-foreground" />
        <p className="text-lg font-medium mb-2">
          {isDragging ? 'Drop files here' : 'Drag & drop files here'}
        </p>
        <p className="text-sm text-muted-foreground mb-4">or click to browse</p>
        <p className="text-xs text-muted-foreground">
          {multiple
            ? `Upload up to ${maxFiles} images (JPEG, PNG, WebP)`
            : 'Upload 1 image (JPEG, PNG, WebP)'}
        </p>
      </Card>

      {previews.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          {previews.map((preview, index) => (
            <div key={index} className="relative group">
              <Card className="overflow-hidden">
                <div className="aspect-square relative">
                  <img
                    src={preview}
                    alt={`Preview ${index + 1}`}
                    className="w-full h-full object-cover"
                  />
                </div>
              </Card>
              <Button
                variant="destructive"
                size="icon"
                className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity"
                onClick={() => removeFile(index)}
              >
                <X className="h-4 w-4" />
              </Button>
              <div className="absolute bottom-2 left-2 right-2">
                <p className="text-xs text-white bg-black/50 rounded px-2 py-1 truncate">
                  {selectedFiles[index].name}
                </p>
              </div>
            </div>
          ))}
        </div>
      )}

      {selectedFiles.length > 0 && (
        <div className="flex items-center justify-between p-4 bg-muted rounded-lg">
          <div className="flex items-center gap-2">
            <ImageIcon className="h-5 w-5 text-muted-foreground" />
            <span className="text-sm font-medium">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
            </span>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSelectedFiles([]);
              setPreviews([]);
              onFilesSelected([]);
            }}
          >
            Clear All
          </Button>
        </div>
      )}
    </div>
  );
}
