#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {

    if (argc < 4) {
        printf("Usage: ./mlpaging <page_size> <vpn1_bits> <vpn2_bits> <pd_entries...> <l2_pt_entries...> <virtual_address>\n");
        return 1;
    }

    int page_size = atoi(argv[1]);
    int vpn1_bits = atoi(argv[2]);
    int vpn2_bits = atoi(argv[3]);

    int pd_size = 1 << vpn1_bits;
    int pt_size = 1 << vpn2_bits;

    int expected_args =
        1 +
        3 +
        pd_size +
        (pd_size * pt_size) +
        1;

    if (argc != expected_args) {
        printf("Usage: ./mlpaging <page_size> <vpn1_bits> <vpn2_bits> <pd_entries...> <l2_pt_entries...> <virtual_address>\n");
        return 1;
    }

    int *pd = malloc(pd_size * sizeof(int));

    int **pt = malloc(pd_size * sizeof(int *));

    for (int i = 0; i < pd_size; i++) {
        pt[i] = malloc(pt_size * sizeof(int));
    }

    int index = 4;

    for (int i = 0; i < pd_size; i++) {
        pd[i] = atoi(argv[index]);
        index++;
    }

    for (int i = 0; i < pd_size; i++) {
        for (int j = 0; j < pt_size; j++) {
            pt[i][j] = atoi(argv[index]);
            index++;
        }
    }

    int va = atoi(argv[index]);

    int vpn = va / page_size;
    int offset = va % page_size;

    int vpn1 = vpn / pt_size;
    int vpn2 = vpn % pt_size;

    if (vpn1 >= pd_size) {
        printf("Segmentation fault\n");
    }

    else if (pd[vpn1] == -1) {
        printf("Segmentation fault\n");
    }

    else if (pt[vpn1][vpn2] == -1) {
        printf("Segmentation fault\n");
    }

    else {

        int pfn = pt[vpn1][vpn2];

        int pa = pfn * page_size + offset;

        printf("Physical address: %d\n", pa);
    }

    for (int i = 0; i < pd_size; i++) {
        free(pt[i]);
    }

    free(pt);
    free(pd);

    return 0;
}