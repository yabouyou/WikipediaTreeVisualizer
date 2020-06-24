from tkinter import *
from PIL import Image, ImageTk
import time
import random
import math
from PageParser import wikiPerson
import numpy as np
import os

start = time.perf_counter()

class ImageTree:
    # static variable for convenient lookup of nodes
    instances = []

    def __init__(self, shape, tag, name_obj, total, canvas, sentences):
        self.__class__.instances.append(self)
        self.shape = shape
        self.tag = tag
        self.name_obj = name_obj
        self.total = total
        self.canvas = canvas
        self.sentences = []
        self.sentence = None
        self.expanded = False
        self.children = []
        self.edges = []

        # parse tag to get the index of node
        node_num = int(tag.split('_')[1])

        if node_num:
            self.sentence = sentences[node_num - 1]

        # left and right child indices for shape number
        left_i = 2 * node_num + 1
        right_i = 2 * node_num + 2

        left_tag = "shape_" + str(left_i)
        right_tag = "shape_" + str(right_i)
        left_name_tag = "name_" + str(left_i)
        right_name_tag = "name_" + str(right_i)

        if right_i < total:
            left_node = canvas.find_withtag(left_tag)
            right_node = canvas.find_withtag(right_tag)

            left_name = canvas.find_withtag(left_name_tag)
            right_name = canvas.find_withtag(right_name_tag)

            # recursive call to make tree with tags as values
            self.children.append(ImageTree(left_node, left_tag, left_name, total, canvas, sentences))
            self.children.append(ImageTree(right_node, right_tag, right_name, total, canvas, sentences))

        elif left_i < total:
            left_node = canvas.find_withtag(left_tag)
            self.children.append(ImageTree(left_node, left_tag, left_name_tag, canvas, total))

    def expand(self):
        if self.children:
            for child in self.children:
                canvas = self.canvas
                child_coords = canvas.coords(child.shape)
                parent_coords = canvas.coords(self.shape)

                # change temporary parent coordinates to point underneath shape
                if self.edges:
                    parent_coords[0] += 50
                    parent_coords[1] += 80
                else:
                    parent_coords[0] -= 10
                    parent_coords[1] += 80


                # change temporary child coordinates to point above shape
                child_coords[0] += 25
                child_coords[1] -= 5

                distance = math.sqrt(
                    ((parent_coords[0] - child_coords[0]) ** 2) + ((parent_coords[1] - child_coords[1]) ** 2))

                sent_coords = [(child_coords[0] + parent_coords[0]) / 2, (child_coords[1] + parent_coords[1]) / 2]


                padding = 25
                if self.edges:
                    new_sent = canvas.create_text(sent_coords[0] + 35, sent_coords[1] - padding * 2,
                                                  text=child.sentence, width=distance,
                                                  tags='sent_' + str(self.total), font=("Times New Roman", 8),
                                                  fill='white')
                else:
                    new_sent = canvas.create_text(sent_coords[0] - 35, sent_coords[1] - padding * 2,
                                                  text=child.sentence, width=distance,
                                                  tags='sent_' + str(self.total), font=("Times New Roman", 8),
                                                  fill='white')

                # keep track of edges and sentences placed so I can delete them later
                self.edges.append(canvas.create_line(child_coords, parent_coords, fill='white'))
                self.sentences.append(new_sent)

                # change child nodes to become visible, i.e. expand tree
                canvas.itemconfig(child.shape, state='normal')
                canvas.itemconfig(child.name_obj, state="normal")

            self.expanded = True

    def collapse(self):
        # recursively collapse all children and sub-children
        if self.children:
            for child in self.children:
                child_tag = child.get_tag()
                child_shape = canvas.find_withtag(child_tag)
                # change child nodes to become hidden
                canvas.itemconfig(child_shape, state='hidden')
                canvas.itemconfig(child.name_obj, state="hidden")
                child.collapse()

            for edge in self.edges:
                canvas.delete(edge)

            self.edges = []

            for sentence in self.sentences:
                canvas.delete(sentence)

            self.expanded = False

    def get_tag(self):
        return self.tag

    def is_expanded(self):
        return self.expanded

    @classmethod
    def get_node_with(cls, tag):
        for ins in cls.instances:
            if ins.get_tag() == tag:
                return ins


def click(event):
    q = event.widget.find_withtag("current")
    canvas = event.widget
    tag = canvas.gettags(q)[0]
    node = ImageTree.get_node_with(tag)

    # ensures only visible images can be expanded
    if node and canvas.itemcget(q, 'state') == "normal":
        if node.is_expanded():
            node.collapse()
        else:
            node.expand()

# initialize window
def init_gui(URL, tree_height):
    tk = Tk()
    WINDOW_HEIGHT = 1000
    WINDOW_WIDTH = 1200
    canvas = Canvas(tk, width=WINDOW_WIDTH, height=WINDOW_HEIGHT)
    canvas.configure(background="#181a1b")
    tk.title("Wikipedia Tree Visualizer")
    if not os.path.exists('images'):
        os.makedirs('images')
    canvas.pack()

    root = None
    root_name = None
    width = WINDOW_WIDTH
    height = 10
    i = 2  # 2 leaf nodes after the first root
    node_count = 0
    size = (50, 50)

    r = wikiPerson(URL, tree_height)


    paths, sentences, names = r.get_bfs_paths()

    while i <= pow(2, tree_height + 1):
        for j in range(1, i, 2):
            # loop through every odd fraction
            # i.e. 1/4, 3/4 for loop of size
            new_shape = None

            # Take the first image retrieved
            curr_img_path = paths.pop(0)
            img = Image.open(curr_img_path)

            # resize the image
            img.thumbnail(size, Image.ANTIALIAS)
            img = ImageTk.PhotoImage(img)

            # keep a reference so that garbage collector doesn't remove it
            label = Label(image=img)
            label.image = img

            # keep track of root element
            # create the n-th image
            curr_state = None
            if node_count == 0:
                curr_state = "normal"
            else:
                curr_state = "hidden"

            img_padding = math.floor(width * (j / i)) - math.floor(width/2)

            new_shape = canvas.create_image(math.floor(width * (j / i)) , height, tags='shape_' + str(node_count),
                                            image=label.image, anchor=NW, state=curr_state)

            coords = canvas.coords(new_shape)
            coords[0] += 20
            coords[1] += 70

            new_name = canvas.create_text(coords[0], coords[1], text=names.pop(0), tags='name_' + str(node_count),
                                          state=curr_state, width=size[0] + 20, fill="white")


            if node_count == 0:
                root = new_shape
                root_name = new_name


            # tag event to click of image
            canvas.tag_bind(new_shape, '<Button-1>', click)
            node_count += 1

        height += 150
        i *= 2

    # create the tree
    x = ImageTree(root, 'shape_0', root_name, node_count, canvas, sentences[:])
    finish = time.perf_counter()
    print(f'Finished in {round(finish-start, 2)} second(s)')
    tk.mainloop()


URL = input("Enter Wikipedia url of a person: ")
tree_height = int(input("How deep would you like the tree? (recommended under 3): "))
init_gui(URL, tree_height)
