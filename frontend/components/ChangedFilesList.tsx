import { FileCode2 } from "lucide-react";
import type { ChangedFile } from "@/types";
import { Badge } from "@/components/ui/badge";

export function ChangedFilesList({ files }: { files: ChangedFile[] }) {
  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th>File</th>
            <th>Status</th>
            <th>Additions</th>
            <th>Deletions</th>
            <th>Changes</th>
          </tr>
        </thead>
        <tbody>
          {files.map((file) => (
            <tr key={file.filename}>
              <td>
                <div className="file-name">
                  <FileCode2 size={16} />
                  <code>{file.filename}</code>
                </div>
                {!file.patch && (
                  <small className="muted">No textual patch available</small>
                )}
              </td>
              <td>
                <Badge variant="outline">{file.status}</Badge>
              </td>
              <td className="text-positive">+{file.additions}</td>
              <td className="text-negative">−{file.deletions}</td>
              <td>{file.changes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
