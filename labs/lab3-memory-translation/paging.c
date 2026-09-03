#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {

    if (argc < 3) {
        printf("Usage: ./paging <page_size> <num_pages> <pfn0> ... <virtual_address>\n");
        exit(1);
    }

    int page_size = atoi(argv[1]);
    int num_pages = atoi(argv[2]);

    if (argc != 3 + num_pages + 1) {
        printf("Usage: ./paging <page_size> <num_pages> <pfn0> ... <virtual_address>\n");
        exit(1);
    }

    int *page_table = malloc(num_pages * sizeof(int));

    for (int i = 0; i < num_pages; i++) {
        page_table[i] = atoi(argv[3 + i]);
    }

    int va = atoi(argv[3 + num_pages]);

    int vpn = va / page_size;
    int offset = va % page_size;

    if (vpn >= num_pages) {
        printf("Segmentation fault\n");
    } else {
        int pfn = page_table[vpn];
        int pa = pfn * page_size + offset;

        printf("Physical address: %d\n", pa);
    }

    free(page_table);

    return 0;
}