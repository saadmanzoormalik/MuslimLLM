"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, RefreshCw, Upload } from "lucide-react";
import { API_BASE, apiGet } from "@/lib/api";
import { Button, Input, Panel, PrimaryButton } from "@/components/ui";

type DocumentRow = {
  id: string;
  title: string;
  author?: string;
  source_type: string;
  madhab: string;
  period: string;
  reliability_level: string;
  chunks: number;
};

export default function AdminPage() {
  const [documents, setDocuments] = useState<DocumentRow[]>([]);
  const [status, setStatus] = useState("");

  function loadDocuments() {
    apiGet<DocumentRow[]>("/documents").then(setDocuments).catch(() => setDocuments([]));
  }

  useEffect(loadDocuments, []);

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setStatus("Uploading and indexing...");
    const form = new FormData(event.currentTarget);
    const response = await fetch(`${API_BASE}/documents/upload`, { method: "POST", body: form });
    setStatus(response.ok ? "Document indexed." : await response.text());
    loadDocuments();
  }

  async function reindex() {
    setStatus("Reindexing seed documents...");
    const response = await fetch(`${API_BASE}/documents/reindex`, { method: "POST" });
    setStatus(response.ok ? "Seed corpus indexed." : await response.text());
    loadDocuments();
  }

  return (
    <main className="min-h-dvh px-4 py-6">
      <div className="mx-auto max-w-6xl">
        <Link className="mb-6 inline-flex items-center gap-2 text-sm text-muted-foreground" href="/"><ArrowLeft size={16} /> Back to chat</Link>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">Document Upload</h1>
            <p className="mt-2 text-muted-foreground">Add txt, md, pdf, json, or csv files with source metadata for pgvector retrieval.</p>
          </div>
          <Button onClick={reindex}><RefreshCw size={16} /> Reindex seed data</Button>
        </div>

        <Panel className="mt-6 p-4">
          <form className="grid gap-3 md:grid-cols-3" onSubmit={upload}>
            <Input name="title" placeholder="Title" required />
            <Input name="author" placeholder="Author" />
            <select name="source_type" className="h-10 rounded-md border bg-card px-3 text-sm">
              {["Quran","Hadith","Tafsir","Fiqh","Sirah","History","Geography","Science","Trade","Military","Geopolitics","Culture","Ethics","Fatwa","Other"].map((x) => <option key={x}>{x}</option>)}
            </select>
            <select name="madhab" className="h-10 rounded-md border bg-card px-3 text-sm">
              {["General","Hanafi","Maliki","Shafi'i","Hanbali","Ja'fari","Zahiri","Unknown"].map((x) => <option key={x}>{x}</option>)}
            </select>
            <select name="period" className="h-10 rounded-md border bg-card px-3 text-sm">
              {["Prophetic","Rashidun","Umayyad","Abbasid","Andalusian","Seljuk","Mamluk","Ottoman","Mughal","Safavid","Modern","Unknown"].map((x) => <option key={x}>{x}</option>)}
            </select>
            <select name="reliability_level" className="h-10 rounded-md border bg-card px-3 text-sm">
              {["Primary","Classical","Modern Academic","Contemporary Scholar","Unknown"].map((x) => <option key={x}>{x}</option>)}
            </select>
            <Input name="geography" placeholder="Geography" />
            <Input name="reference" placeholder="Reference" />
            <Input name="language" placeholder="Language" defaultValue="English" />
            <Input name="copyright_status" placeholder="Copyright status" defaultValue="Public domain / sample" />
            <Input name="uploaded_by" placeholder="Uploaded by" defaultValue="admin" />
            <Input name="file" type="file" accept=".txt,.md,.pdf,.json,.csv" required />
            <PrimaryButton className="md:col-span-3" type="submit"><Upload size={16} /> Upload and index</PrimaryButton>
          </form>
          {status ? <p className="mt-3 text-sm text-muted-foreground">{status}</p> : null}
        </Panel>

        <div className="mt-6 overflow-hidden rounded-lg border">
          <table className="w-full text-left text-sm">
            <thead className="bg-muted">
              <tr>
                <th className="p-3">Title</th>
                <th className="p-3">Type</th>
                <th className="p-3">Madhab</th>
                <th className="p-3">Period</th>
                <th className="p-3">Reliability</th>
                <th className="p-3">Chunks</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id} className="border-t">
                  <td className="p-3">{doc.title}</td>
                  <td className="p-3">{doc.source_type}</td>
                  <td className="p-3">{doc.madhab}</td>
                  <td className="p-3">{doc.period}</td>
                  <td className="p-3">{doc.reliability_level}</td>
                  <td className="p-3">{doc.chunks}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
