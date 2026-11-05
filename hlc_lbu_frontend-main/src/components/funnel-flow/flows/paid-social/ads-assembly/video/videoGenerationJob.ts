import { NetworkError, RequestTimeoutError } from "@/services/common-errors";
import VideoApi, {
  VideoDraft,
  VideoJobProgress,
} from "@/services/funnel-flow/paid-social/VideoApi";

const POLL_INTERVAL_MS = 3 * SECOND_IN_MS;
/** A job with no shot changing for this long is taken as stuck. */
const STALE_MS = 5 * MINUTE_IN_MS;
/** The longest a generation is waited for, from when it started. */
const MAX_WAIT_MS = 20 * MINUTE_IN_MS;
/**
 * The draft is saved after the job completes, so it's waited for a bit. Past
 * this the step goes on: either no shot succeeded, or the save failed.
 */
const SAVE_WAIT_MS = 20 * SECOND_IN_MS;

/**
 * The generation didn't finish in time, or stopped moving. It may still finish
 * in the background, so it's not reported as a failure.
 */
export class GenerationTakingTooLongError extends Error {
  constructor() {
    super("GENERATION_TAKING_TOO_LONG");
    this.name = this.constructor.name;
  }
}

/**
 * Whether a generation request ended without knowing if it worked: the
 * backend stopped waiting, or the connection dropped. The generation goes on.
 */
export function isGenerationOutcomeUnknown(error: unknown) {
  return error instanceof RequestTimeoutError || error instanceof NetworkError;
}

/** Counts of a job's shots, for the loading screen. */
export function getJobShotCounts(job: VideoJobProgress | undefined) {
  const shots = job?.variants.flatMap((variant) => variant.shots) ?? [];

  return {
    total: shots.length,
    ready: shots.filter((shot) => shot.status === "READY").length,
    failed: shots.filter((shot) => shot.status === "FAILED").length,
  };
}

/**
 * Follows a generation from the job the backend writes to the draft when it
 * starts. The generate endpoints only answer once the generation ends, so the
 * job is what gives the progress while they run, and what tells when the
 * generation ended if the request times out.
 *
 * Polls while the request runs, until `stop()`. After a request that ended
 * without an answer, `waitForResult()` waits for the generation instead.
 *
 * TODO: start from the job id the endpoints return once they answer right
 * away, instead of finding it in the draft.
 */
export function watchVideoGenerationJob(options: {
  adId: number;
  /**
   * The step the backend saves the job id under, in the draft's `jobs`.
   * Without it (assembling has no job), only the draft is followed.
   */
  step?: string;
  /** The job id the draft had before, so it isn't taken for the new one. */
  previousJobId?: string;
}) {
  const progress = shallowRef<VideoJobProgress>();

  const startedAt = Date.now();
  let jobId: string | undefined;
  let lastChangeAt = startedAt;
  let lastShotStatuses: string | undefined;
  let isStopped = false;
  let isWaiting = false;

  async function readDraft() {
    try {
      return await VideoApi.getDraft(options.adId);
    } catch (error) {
      console.error("Failed to read the draft of the generation:", error);
      return undefined;
    }
  }

  // The job id from the draft until it shows up, then the job. A failed read
  // is skipped, the next one may work. Returns the draft if it read one, so
  // it isn't read twice in the same poll
  async function refresh() {
    if (!options.step) return undefined;

    let draft: VideoDraft | undefined;

    if (!jobId) {
      draft = await readDraft();
      const id = draft?.jobs?.[options.step];
      if (id && id !== options.previousJobId) jobId = id;
    }

    if (!jobId) return draft;

    try {
      const job = await VideoApi.getJobProgress(jobId);
      if (!job) return draft;

      const shotStatuses = job.variants
        .flatMap((variant) => variant.shots.map((shot) => shot.status))
        .join();
      if (shotStatuses !== lastShotStatuses) {
        lastShotStatuses = shotStatuses;
        lastChangeAt = Date.now();
      }

      progress.value = job;
    } catch (error) {
      console.error("Failed to read the generation progress:", error);
    }

    return draft;
  }

  // The progress while the request runs. Without a job there's none to show
  void (async () => {
    while (
      options.step &&
      !isStopped &&
      !isWaiting &&
      !progress.value?.complete
    ) {
      await refresh();
      await sleep(POLL_INTERVAL_MS);
    }
  })();

  /**
   * Resolves once the result is in the draft (`isSaved`), or the job
   * completed and the save was waited for. Without a job to follow, only the
   * draft tells. Throws `GenerationTakingTooLongError` when the job stops
   * moving or it's waited too long.
   */
  async function waitForResult(isSaved: (draft: VideoDraft) => boolean) {
    isWaiting = true;
    let completedAt: number | undefined;

    while (!isStopped) {
      const refreshedDraft = await refresh();

      const now = Date.now();
      const job = progress.value;

      if (now - startedAt > MAX_WAIT_MS) {
        throw new GenerationTakingTooLongError();
      }

      if (job && !job.complete && now - lastChangeAt > STALE_MS) {
        throw new GenerationTakingTooLongError();
      }

      if (!job || job.complete) {
        const draft = refreshedDraft ?? (await readDraft());
        if (draft && isSaved(draft)) return;

        if (job?.complete) {
          completedAt ??= now;
          if (now - completedAt > SAVE_WAIT_MS) return;
        }
      }

      await sleep(POLL_INTERVAL_MS);
    }
  }

  function stop() {
    isStopped = true;
  }

  return { progress, waitForResult, stop };
}
