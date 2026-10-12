"""Type proposals: look for kinds of knowledge the ontology has no entity for (OKF redesign step 5). No file of the bundle or the code is written.

Per ingested original (after extraction and discovery), the chunks whose content is in no knowledge fact (UNMAPPED, SKIPPED_SCOPE, or kept as a
note) go in batches, one fresh single-tool call per batch (`TypeProposer`) returns zero or more proposed entity types; code checks them
(`proposal_tools`), merges repeats of one name and stores the new ones as pending proposals (`ProposalStore`). Unchanged chunks are not asked
again. Turning a proposal into a model is a separate, gated developer step (`agents/apply_type_proposal.py`).
"""
from docfactory.agents.type_proposer import TypeProposer
from docfactory.bundle.source_store import SourceStore
from docfactory.extract.batching import batch_chunks, chunks_hash
from docfactory.extract.coverage import LOST, file_coverage
from docfactory.ingest.source_reads import read_chunks
from docfactory.models.coverage_status import CoverageStatus
from docfactory.models.proposal_report import ProposalReport
from docfactory.models.type_proposal import TypeProposal
from docfactory.ontology.proposal_store import ProposalStore


def propose_types(path: str, proposer: TypeProposer, force: bool = False) -> ProposalReport:
    """Look for new entity types in the chunks of the ingested original `path` that are in no knowledge fact and return the report.

    `force` asks again although the chunks are unchanged. Raises FileNotFoundError for an original with no Source.
    """
    path = path.replace("\\", "/").strip("/")
    if SourceStore().read(path) is None:
        raise FileNotFoundError(f"no such file in the bundle: {path}")
    wanted = {c.chunk_no for c in file_coverage(path).chunks if c.status in LOST or c.status == CoverageStatus.NOTED}
    if not wanted:
        return ProposalReport(path=path, reason="every chunk is in a knowledge fact")
    _, all_chunks = read_chunks(path)
    chunks = [c for c in all_chunks if c.chunk_no in wanted]
    current_hash = chunks_hash(chunks)
    store = ProposalStore()
    if store.asked(path) == current_hash and not force:
        return ProposalReport(path=path, chunks_asked=len(chunks), reason="the chunks that are in no fact are unchanged since the last look")
    pending = batch_chunks(chunks)
    found: dict[str, TypeProposal] = {}
    calls, failed, notes = 0, 0, []
    while pending:
        batch = pending.pop(0)
        proposals, note = proposer.propose_batch(path, batch)
        calls += 1
        if proposals is None:
            label = f"chunks {batch[0].chunk_no}-{batch[-1].chunk_no}"
            if len(batch) > 1:
                half = len(batch) // 2
                pending[:0] = [batch[:half], batch[half:]]
                notes.append(f"{label}: {note}; split and retried in two halves")
            else:
                failed += 1
                notes.append(f"{label}: {note}")
            continue
        for proposal in proposals:
            proposal = proposal.model_copy(update={"source_path": path, "proposed_by": proposer.actor})
            if proposal.entity in found:  # the same type proposed from another batch: keep the first, add the chunks
                known = found[proposal.entity]
                found[proposal.entity] = known.model_copy(update={"sample_chunks": sorted(set(known.sample_chunks) | set(proposal.sample_chunks))})
            else:
                found[proposal.entity] = proposal
    saved = [name for name, proposal in found.items() if store.save(proposal)]
    if not failed:
        store.mark_asked(path, current_hash)
    return ProposalReport(path=path, chunks_asked=len(chunks), batches=calls, failed_batches=failed, saved=saved,
                          already_known=[name for name in found if name not in saved], batch_notes=notes,
                          reason="" if saved else "no new entity type was proposed")


def format_proposals(report: ProposalReport) -> str:
    """The plain-text report of one proposal run."""
    lines = [f"{report.path}: type proposals"]
    if report.batches:
        lines.append(f"  chunks {report.chunks_asked}, batches {report.batches} ({report.failed_batches} failed)")
    lines += [f"  proposed {name} (pending): python -m docfactory.agents.apply_type_proposal {name}" for name in report.saved]
    lines += [f"  {name}: already proposed" for name in report.already_known]
    lines += [f"  {note}" for note in report.batch_notes]
    if report.reason:
        lines.append(f"  reason: {report.reason}")
    return "\n".join(lines)
