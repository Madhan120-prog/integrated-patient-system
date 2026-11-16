"""Turn one of our public NIfTI cases back into a DICOM CT + the doctor's RTSTRUCT, zipped, to try the prototype
when no DICOM is on this computer. (Better: copy a real public patient folder from BigBlue, see README.)

    .venv/bin/python prototype/make_sample.py data/nnunet/Dataset001_LungGTV LUNG1-006 prototype/samples
"""
import sys
import tempfile
import zipfile
from pathlib import Path

import numpy as np

import SimpleITK as sitk
from pydicom.dataset import FileDataset, FileMetaDataset
from pydicom.uid import CTImageStorage, ExplicitVRLittleEndian, generate_uid

sys.path.insert(0, str(Path(__file__).resolve().parent))
from engine import slice_order  # noqa: E402


def write_ct(ct: sitk.Image, pid: str, out: Path):
    arr = sitk.GetArrayFromImage(ct).astype(np.int16)
    d = np.array(ct.GetDirection()).reshape(3, 3)
    iop = [*d[:, 0], *d[:, 1]]
    study, series, frame = generate_uid(), generate_uid(), generate_uid()
    for z in range(arr.shape[0]):
        meta = FileMetaDataset()
        meta.MediaStorageSOPClassUID, meta.MediaStorageSOPInstanceUID = CTImageStorage, generate_uid()
        meta.TransferSyntaxUID = ExplicitVRLittleEndian
        ds = FileDataset(None, {}, file_meta=meta, preamble=b"\0" * 128)
        ds.SOPClassUID, ds.SOPInstanceUID = CTImageStorage, meta.MediaStorageSOPInstanceUID
        ds.Modality, ds.PatientID, ds.PatientName = "CT", pid, pid
        ds.StudyInstanceUID, ds.SeriesInstanceUID, ds.FrameOfReferenceUID = study, series, frame
        ds.StudyDate, ds.StudyTime, ds.StudyID, ds.SeriesNumber, ds.InstanceNumber = "20000101", "120000", "1", 1, z + 1
        ds.ImagePositionPatient = [float(v) for v in ct.TransformIndexToPhysicalPoint((0, 0, z))]
        ds.ImageOrientationPatient = [float(v) for v in iop]
        ds.PixelSpacing = [float(ct.GetSpacing()[1]), float(ct.GetSpacing()[0])]
        ds.SliceThickness = float(ct.GetSpacing()[2])
        ds.Rows, ds.Columns = arr.shape[1:]
        ds.SamplesPerPixel, ds.PhotometricInterpretation = 1, "MONOCHROME2"
        ds.BitsAllocated, ds.BitsStored, ds.HighBit, ds.PixelRepresentation = 16, 16, 15, 1
        ds.RescaleIntercept, ds.RescaleSlope = 0, 1
        ds.PixelData = arr[z].tobytes()
        ds.save_as(out / f"ct_{z:04d}.dcm", enforce_file_format=True)


def main(data, pid, out):
    from rt_utils import RTStructBuilder
    data, out = Path(data), Path(out)
    ct = sitk.ReadImage(str(data / "imagesTr" / f"{pid}_0000.nii.gz"))
    lab = sitk.GetArrayFromImage(sitk.ReadImage(str(data / "labelsTr" / f"{pid}.nii.gz")))
    with tempfile.TemporaryDirectory() as tmp:
        ct_dir = Path(tmp) / "ct"
        ct_dir.mkdir()
        write_ct(ct, pid, ct_dir)
        rt = RTStructBuilder.create_new(dicom_series_path=str(ct_dir))
        rt.add_roi(mask=lab[slice_order(ct_dir)].transpose(1, 2, 0).astype(bool), name="GTV-1", color=[0, 200, 255])
        rt.save(str(Path(tmp) / "rtstruct.dcm"))
        out.mkdir(parents=True, exist_ok=True)
        zpath = out / f"{pid}_sample.zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(Path(tmp).rglob("*.dcm")):
                z.write(f, f.relative_to(tmp))
    print(f"{zpath}: {ct.GetSize()[2]} CT slices + the doctor's GTV-1")


if __name__ == "__main__":
    main(*sys.argv[1:4])
