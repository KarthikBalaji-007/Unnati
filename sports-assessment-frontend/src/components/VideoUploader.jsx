/**
 * VideoUploader.jsx
 * Drag-and-drop or click-to-browse video file uploader with preview.
 */

import { useState, useRef, useCallback } from 'react';

export default function VideoUploader({ onFileSelected }) {
    const [dragOver, setDragOver] = useState(false);
    const [preview, setPreview] = useState(null);
    const [fileName, setFileName] = useState('');
    const inputRef = useRef(null);

    const handleFile = useCallback((file) => {
        if (!file) return;
        if (!file.type.startsWith('video/')) {
            alert('Please upload a video file (mp4, webm, avi, etc.)');
            return;
        }
        const url = URL.createObjectURL(file);
        setPreview(url);
        setFileName(file.name);
        onFileSelected(file);
    }, [onFileSelected]);

    const onDrop = useCallback((e) => {
        e.preventDefault();
        setDragOver(false);
        const file = e.dataTransfer.files?.[0];
        handleFile(file);
    }, [handleFile]);

    const onInputChange = (e) => handleFile(e.target.files?.[0]);

    const clearPreview = () => {
        if (preview) URL.revokeObjectURL(preview);
        setPreview(null);
        setFileName('');
        onFileSelected(null);
        if (inputRef.current) inputRef.current.value = '';
    };

    return (
        <div>
            {!preview ? (
                <div
                    className={`drop-zone ${dragOver ? 'drag-over' : ''}`}
                    onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
                    onDragLeave={() => setDragOver(false)}
                    onDrop={onDrop}
                    onClick={() => inputRef.current?.click()}
                >
                    <input ref={inputRef} type="file" accept="video/*" onChange={onInputChange} />
                    <div style={{ fontSize: '3rem', marginBottom: '12px' }}>
                        {dragOver ? '📂' : '🎬'}
                    </div>
                    <h3 style={{ marginBottom: '8px', color: 'var(--text-primary)' }}>
                        {dragOver ? 'Drop video here' : 'Upload Video'}
                    </h3>
                    <p style={{ fontSize: '0.9rem' }}>
                        Drag & drop or click to browse
                    </p>
                    <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '8px' }}>
                        Supports MP4, WebM, AVI, MOV – max 500 MB
                    </p>
                </div>
            ) : (
                <div>
                    <div className="video-container">
                        <video src={preview} controls style={{ maxHeight: '360px', width: '100%' }} />
                    </div>
                    <div className="flex gap-3 items-center" style={{ marginTop: '12px' }}>
                        <div style={{ flex: 1, fontSize: '0.85rem', color: 'var(--text-secondary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            📎 {fileName}
                        </div>
                        <button className="btn btn-secondary btn-sm" onClick={clearPreview}>
                            ✕ Remove
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
}
