## 5. Chunking

# Implement a function that splits a long string into chunks by character 
# count, with a fixed overlap between consecutive chunks. It should return 
# a list of chunk objects that include at least `chunk_index`, `content`,
#  `start_offset`, and `end_offset`. Enforce that overlap is less than 
# chunk size; the last chunk may be shorter. Optionally add a test: for a 
# short string and given `chunk_size` and `overlap`, the start offsets and
#  content match what you expect.


# Part B — Chunking (document → chunks)
# Prompt B1 — Implement chunking by characters

# Create chunking.py with:
# def chunk_text_chars(text: str, chunk_size: int, overlap: int) -> list[Chunk]

# Chunk should include:

# chunk_index
# content
# start_offset
# end_offset

# Rules:
# overlap must be < chunk_size
# last chunk can be shorter
# offsets must match the original text slice
# Test yourself
# If chunk_size=10 and overlap=2, verify start positions: 0, 8, 16, ...

#“In chunk_text_chars, at the start of the function, validate that overlap is less than chunk_size. If overlap >= chunk_size, raise ValueError with message 'overlap must be less than chunk size'.”


# “Implement the body of chunk_text_chars: split text into overlapping 
# chunks of length chunk_size with overlap characters between consecutive 
# chunks. Use step = chunk_size - overlap. For each chunk store: 
# start_offset, end_offset (slice into text), content (the slice), 
# and chunk_index (0, 1, 2, …). The last chunk may be shorter than chunk_size. 
# Return a list of Chunk instances.”


from dataclasses import dataclass


@dataclass
class Chunk():
    chunk_index: int        # created by putting doc_id : then chunk_index in a string (e.g. report-2024:0)
    content: str
    start_offset: int
    end_offset: int

def chunk_text_chars(text: str, 
    chunk_size: int, 
    overlap: int) -> list[Chunk]:
    if overlap >= chunk_size:
        raise ValueError ("overlap must be less than chunk size")

    list_of_chunks = []
    step = chunk_size - overlap 
    for start in range(0, len(text), step):
        #start_offset = chunk
        end = min(start + chunk_size, len(text))    #whichever is less
        chunk = text[start:end]
        chunk_index = len(list_of_chunks)

        list_of_chunks.append(Chunk(
            chunk_index=chunk_index,
            content = chunk,
            start_offset=start,
            end_offset=end
        ))

    return list_of_chunks


# test:
# chunk_size = 5
# overlap = 2
# abcdefghijklmnopqrstuvwxyz
# step = chunk_size - overlap    = 5-2 = 3

# first pass
# chunk from 0 to 4 (abcde)
# start = start = 0
# end = start + chunk size = 4

#second pass
# chunk from 3 to 7 (cdefg)
# start = 3
# end = start + chunk size = 4


# if __name__ == "__main__":
#     text = "abcdefghijklmnopqrstuvwxyz"
#     chunks = chunk_text_chars(text, chunk_size=10, overlap=2)
#     for c in chunks:
#         print(c)
#     # Spec: start positions 0, 8, 16, ...
#     assert [c.start_offset for c in chunks] == [0, 8, 16,24]
#     assert len(chunks) == 4
#     print ("ok")