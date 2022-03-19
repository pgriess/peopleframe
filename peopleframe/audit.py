# NOTES:
#
#   - You can run `automator -i /path/to/input/file /path/to/workflow` to runs
#     an Automator workflow that requires a File input; we have a `Display
#     referenced photo` in the root of the repository
#
#   - There are several PersonInfo objects with the name '_UNKNOWN_'; each
#     represents what is considered to be an independent person. Each of these
#     has several FaceInfo objects describing their different faces.
#
#   - Unknown if it is possible to find FaceInfo objects that represent faces
#     found in multiple photos, or if they are each single-photo and are
#     aggregated at the PersonInfo layer.
#
#   - The FaceInfo object has (x, y) coordinates for the face location in the
#     image. The range is [0, 1.0]
#
#   - The FaceInfo object has a quality(?) score q=[-1.0, 1.0]. There are some
#     PersonInfo objects with FaceInfo objects that are exclusively -1. One is
#     Mia. But this FaceInfo doesn't actually show up rendered in the Photos
#     application.
#
#       - TODO: Does this FaceInfo have coordinates?
#
#   - Each photo can have multiple FaceInfo associated with it, each with a
#     different PersonInfo.
#
#   - Tagging a single FaceInfo in a PersonInfo doesn't seem to update the rest
#     of the FaceInfos. At least not immediately. Maybe this happens in the
#     background?
#
#       - TODO: Test this
#
#   TODO:
#
#       - Need a way to mark people so that they don't show up in the tool
#         anymore, e.g. someone who we don't know or care about.
#
#       - Need a way to mark photos so that they don't show up in the tool
#         anymore, e.g. a photo that has ONLY people that we don't care about.

from functools import partial
import os.path
from subprocess import check_call
import sys

import osxphotos
from PyQt6.QtWidgets import (
    QApplication,
    QLabel,
    QStyle,
    QWidget,
    QGridLayout,
    QVBoxLayout,
    QPushButton,
)
from PyQt6.QtGui import QGuiApplication, QImage, QPixmap, QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QSize, QPoint, pyqtSignal, pyqtSlot


class PersonWidget(QWidget):
    """
    A QWidget representing providing functionality for interacting with a
    PersonInfo.
    """

    person: osxphotos.PersonInfo
    open_person: pyqtSignal = pyqtSignal(osxphotos.PersonInfo)

    def __init__(self, person: osxphotos.PersonInfo, parent=None):
        super(PersonWidget, self).__init__(parent)

        self.person = person

        image = self.load_person_image(person)
        layout = QVBoxLayout(self)
        label = QLabel()
        layout.addWidget(label)
        label.setPixmap(
            QPixmap.fromImage(image).scaled(
                400, 400, Qt.AspectRatioMode.KeepAspectRatio
            )
        )

        pb = QPushButton("Open")
        pb.clicked.connect(lambda: self.open_person.emit(self.person))
        layout.addWidget(pb)

    def load_person_image(self, person: osxphotos.PersonInfo) -> QImage:
        """Load a QImage representing the given PersonInfo."""

        for fi in person.face_info:
            if fi._pk == person.keyface:
                break

        qi = QImage(person.keyphoto.path)
        qp = QPainter(qi)
        pen = QPen(QColor.fromRgb(255, 0, 255))
        pen.setWidth(20)
        qp.setPen(pen)

        qp.drawEllipse(
            QPoint(fi.center[0], fi.center[1]),
            # XXX: What is the right rx/ry?
            int(fi.size * fi.source_width),
            int(fi.size * fi.source_width),
        )

        return qi


def main():
    app = QApplication(sys.argv)
    widget = QWidget()

    layout = QGridLayout(widget)

    people = []
    pdb = osxphotos.PhotosDB()
    for pi in sorted(
        [pi for pi in pdb.person_info if pi.facecount > 0 and pi.name == "_UNKNOWN_"],
        key=lambda pi: pi.facecount,
        reverse=True,
    ):
        # XXX: Why?
        if not pi.keyface:
            continue

        # XXX: Why?
        if not pi.keyphoto:
            continue

        people.append(pi)
        if len(people) >= 9:
            break

    for r in range(3):
        for c in range(3):
            pi = people[r * 3 + c]

            @pyqtSlot()
            def click(person: osxphotos.PersonInfo):
                print(f"photo={person.uuid}: path={person.keyphoto.path}")

                check_call(
                    args=[
                        "automator",
                        "-i",
                        person.keyphoto.path,
                        os.path.join(
                            os.path.dirname(__file__),
                            "..",
                            "Display referenced photo.workflow",
                        ),
                    ]
                )

            pw = PersonWidget(pi)
            pw.open_person.connect(click)

            layout.addWidget(pw, r, c)

    # Center the window
    #
    # XXX: This is broken. It's centering the top-left corner.
    widget.setGeometry(
        QStyle.alignedRect(
            Qt.LayoutDirection.LeftToRight,
            Qt.AlignmentFlag.AlignCenter,
            layout.geometry().size(),
            QGuiApplication.primaryScreen().availableGeometry(),
        )
    )
    widget.setWindowTitle("PyQt6 Example")
    widget.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
