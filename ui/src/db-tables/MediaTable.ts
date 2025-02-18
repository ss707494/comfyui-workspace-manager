import { saveDB } from "../Api";
import { v4 as uuidv4 } from "uuid";
import { Table, getWorkflow, updateFlow } from "./WorkspaceDB";
import { updateWorkspaceIndexDB } from "./IndexDBUtils";
import { TableBase } from "./TableBase";
import { Media } from "../types/dbTypes";
import { indexdb } from "./indexdb";

export class MediaTable extends TableBase<Media> {
  static readonly TABLE_NAME: Table = "media";
  constructor() {
    super("media");
  }
  public async listByWorkflowID(workflowID: string): Promise<Media[]> {
    const records = await this.getRecords();
    return Object.values(records)
      .filter((c) => c.workflowID === workflowID)
      .sort((a, b) => b.createTime - a.createTime);
  }

  public async getLastestByWorkflowID(workflowID: string): Promise<Media> {
    const records = await this.getRecords();
    const all = Object.values(records)
      .filter((c) => c.workflowID === workflowID)
      .sort((a, b) => b.createTime - a.createTime);
    return all[0];
  }

  public async create(input: {
    localPath: string;
    workflowID: string;
  }): Promise<Media | null> {
    const format = input.localPath.split(".").pop();
    if (format == null) return null;
    const md: Media = {
      id: uuidv4(),
      localPath: input.localPath,
      workflowID: input.workflowID,
      createTime: Date.now(),
      format: format,
    };
    //link media to workflow
    const curMedia = getWorkflow(input.workflowID)?.mediaIDs ?? [];
    const newMedia = new Set(curMedia).add(md.id);
    updateFlow(input.workflowID, {
      mediaIDs: Array.from(newMedia),
      coverMediaPath: md.localPath,
    });
    // save indexdb
    // indexdb.media.add(md);
    const records = await this.getRecords();
    records[md.id] = md;
    // save disk file db
    saveDB("media", JSON.stringify(records));
    // save legacy indexdb backup
    updateWorkspaceIndexDB();
    return md;
  }
}
