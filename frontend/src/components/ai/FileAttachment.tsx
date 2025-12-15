"use client";

import React from 'react';
import { FileText, Download, File, FileSpreadsheet, FileCode, FileImage, FileVideo, FileAudio } from 'lucide-react';

export interface FileAttachmentProps {
  url?: string;
  asset_url?: string;
  title?: string;
  title_link?: string;
  text?: string;
  file_size?: number;
  mime_type?: string;
  type?: string;
}

/**
 * File Attachment Component for displaying file attachments in chat
 *
 * Supports:
 * - Document files (PDF, DOC, DOCX, TXT, XLS, XLSX, PPT, PPTX)
 * - Icons based on file type
 * - File size display
 * - Download functionality
 */
export const FileAttachment: React.FC<FileAttachmentProps> = ({
  url,
  asset_url,
  title,
  title_link,
  text,
  file_size,
  mime_type,
  type,
}) => {
  const fileUrl = url || asset_url || title_link || '';
  const fileName = title || 'Untitled file';

  if (!fileUrl) {
    console.warn('[FileAttachment] No file URL provided');
    return null;
  }

  // Determine file icon based on mime_type or file extension
  const getFileIcon = () => {
    const mimeType = mime_type?.toLowerCase() || '';
    const ext = fileName.split('.').pop()?.toLowerCase() || '';

    // PDFs
    if (mimeType.includes('pdf') || ext === 'pdf') {
      return <FileText className="w-8 h-8 text-red-400" />;
    }

    // Word documents
    if (mimeType.includes('word') || mimeType.includes('msword') || ['doc', 'docx'].includes(ext)) {
      return <FileText className="w-8 h-8 text-blue-400" />;
    }

    // Excel spreadsheets
    if (mimeType.includes('excel') || mimeType.includes('spreadsheet') || ['xls', 'xlsx', 'csv'].includes(ext)) {
      return <FileSpreadsheet className="w-8 h-8 text-green-400" />;
    }

    // PowerPoint
    if (mimeType.includes('powerpoint') || mimeType.includes('presentation') || ['ppt', 'pptx'].includes(ext)) {
      return <FileText className="w-8 h-8 text-orange-400" />;
    }

    // Code files
    if (['js', 'jsx', 'ts', 'tsx', 'py', 'java', 'cpp', 'c', 'html', 'css', 'json', 'xml'].includes(ext)) {
      return <FileCode className="w-8 h-8 text-purple-400" />;
    }

    // Images
    if (mimeType.includes('image') || ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp'].includes(ext)) {
      return <FileImage className="w-8 h-8 text-cyan-400" />;
    }

    // Videos
    if (mimeType.includes('video') || ['mp4', 'mov', 'avi', 'webm', 'mkv'].includes(ext)) {
      return <FileVideo className="w-8 h-8 text-pink-400" />;
    }

    // Audio
    if (mimeType.includes('audio') || ['mp3', 'wav', 'ogg', 'm4a', 'flac'].includes(ext)) {
      return <FileAudio className="w-8 h-8 text-yellow-400" />;
    }

    // Default file icon
    return <File className="w-8 h-8 text-slate-400" />;
  };

  // Format file size
  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleDownload = async (e: React.MouseEvent) => {
    e.preventDefault();
    try {
      const response = await fetch(fileUrl);
      const blob = await response.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = blobUrl;
      link.download = fileName;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(blobUrl);
    } catch (error) {
      console.error('[FileAttachment] Download failed:', error);
      // Fallback: open in new tab
      window.open(fileUrl, '_blank');
    }
  };

  return (
    <div className="max-w-md">
      <a
        href={fileUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="flex items-center gap-3 p-4 rounded-lg border border-slate-700 hover:border-blue-500 bg-slate-900/50 hover:bg-slate-800/70 transition-all group"
      >
        {/* File Icon */}
        <div className="flex-shrink-0">
          {getFileIcon()}
        </div>

        {/* File Info */}
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-slate-200 truncate group-hover:text-blue-400 transition-colors">
            {fileName}
          </p>
          {text && (
            <p className="text-xs text-slate-400 mt-1 line-clamp-2">{text}</p>
          )}
          <div className="flex items-center gap-2 mt-1">
            {file_size && (
              <span className="text-xs text-slate-500">
                {formatFileSize(file_size)}
              </span>
            )}
            {mime_type && (
              <span className="text-xs text-slate-500">
                {mime_type.split('/').pop()?.toUpperCase()}
              </span>
            )}
          </div>
        </div>

        {/* Download Button */}
        <button
          onClick={handleDownload}
          className="flex-shrink-0 p-2 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
          title="Download file"
        >
          <Download className="w-4 h-4 text-slate-300" />
        </button>
      </a>
    </div>
  );
};
